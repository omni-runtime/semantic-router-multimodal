"""Small native WebSocket example client; requires a deployed gateway."""
import base64
import hashlib
import json
import os
import socket
import ssl
import struct
import time
from urllib.parse import urlsplit, urlencode
import uuid


def frame_record(opcode, payload):
    return {"opcode":opcode,"sha256":hashlib.sha256(payload).hexdigest(),"bytes":len(payload)}


class WebSocket:
    def __init__(self, gateway, path, token, request_id, extra=None):
        url = urlsplit(gateway)
        self.sock = socket.create_connection((url.hostname, url.port or (443 if url.scheme == "https" else 80)), timeout=15)
        if url.scheme == "https": self.sock = ssl.create_default_context().wrap_socket(self.sock,server_hostname=url.hostname)
        self.buffer = bytearray()
        self.sent, self.received = [], []
        self.key = base64.b64encode(os.urandom(16)).decode()
        headers = {"Host":url.netloc,"Upgrade":"websocket","Connection":"Upgrade",
                   "Sec-WebSocket-Version":"13","Sec-WebSocket-Key":self.key,"X-Request-ID":request_id}
        if token: headers["Authorization"]="Bearer "+token
        headers.update(extra or {})
        self.sock.sendall(("GET "+path+" HTTP/1.1\r\n"+"".join(k+": "+v+"\r\n" for k,v in headers.items())+"\r\n").encode())
        while b"\r\n\r\n" not in self.buffer:
            data=self.sock.recv(4096)
            if not data: raise EOFError("EOF during handshake")
            self.buffer.extend(data)
            if len(self.buffer)>65536: raise ValueError("oversized handshake")
        head, _, body=self.buffer.partition(b"\r\n\r\n"); self.buffer=bytearray(body)
        lines=head.decode("latin-1").split("\r\n"); self.status=int(lines[0].split()[1])
        self.headers={k.lower():v.strip() for k,v in (line.split(":",1) for line in lines[1:])}
        if self.status==101:
            expected=base64.b64encode(hashlib.sha1((self.key+"258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()).decode()
            assert self.headers.get("sec-websocket-accept")==expected, "invalid native upgrade acceptance"
            assert self.headers.get("upgrade","").lower()=="websocket", "upgrade header lost"

    def send(self, payload, opcode=1, final=True):
        if isinstance(payload,dict): payload=json.dumps(payload,separators=(",",":")).encode()
        if isinstance(payload,str): payload=payload.encode()
        assert len(payload)<=131072
        mask=os.urandom(4); length=len(payload); first=(128 if final else 0)|opcode
        prefix=(bytes([first,128|length]) if length<126 else bytes([first,128|126])+struct.pack(">H",length) if length<65536 else bytes([first,128|127])+struct.pack(">Q",length))
        self.sock.sendall(prefix+mask+bytes(b^mask[i%4] for i,b in enumerate(payload)))
        self.sent.append(frame_record(opcode,payload))

    def exact(self,count):
        while len(self.buffer)<count:
            data=self.sock.recv(min(65536,count-len(self.buffer)))
            if not data: raise EOFError("native peer disconnected")
            self.buffer.extend(data)
        result=bytes(self.buffer[:count]);del self.buffer[:count];return result

    def receive(self):
        first,second=self.exact(2); opcode=first&15; length=second&127
        assert first&128 and not first&112 and not second&128, "invalid server frame"
        if length==126: length=struct.unpack(">H",self.exact(2))[0]
        elif length==127: length=struct.unpack(">Q",self.exact(8))[0]
        assert length<=2*1024*1024,"oversized server frame"
        payload=self.exact(length);self.received.append(frame_record(opcode,payload));return opcode,payload

    def event(self):
        opcode,data=self.receive();assert opcode==1,"expected text event";return json.loads(data)

    def close(self):
        if self.status==101:
            self.send(struct.pack(">H",1000),8)
            opcode,payload=self.receive();assert opcode==8 and payload[:2]==struct.pack(">H",1000),"close handshake changed"
        self.sock.close()



if __name__ == "__main__":
    import argparse
    import sys
    from pathlib import Path
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task",choices=["speech","realtime"])
    parser.add_argument("--model",default="auto",help="Public SR entrypoint")
    parser.add_argument("--text",default="Hello. Have a good day.")
    parser.add_argument("--voice",default="Vivian")
    parser.add_argument("--max-new-tokens",type=int,default=96)
    parser.add_argument("--audio",type=Path,help="16 kHz mono PCM16 input for realtime")
    parser.add_argument("--audio-output",action="store_true")
    args=parser.parse_args()
    if args.task=="realtime" and args.audio is None: parser.error("realtime requires --audio")
    query={"model":args.model}
    if args.task=="realtime": query.update(sr_input="audio",sr_output="text,audio" if args.audio_output else "text")
    path=("/v1/audio/speech/stream" if args.task=="speech" else "/v1/realtime")+"?"+urlencode(query)
    client=WebSocket(os.environ["GATEWAY_URL"],path,os.environ["GATEWAY_TOKEN"],str(uuid.uuid4()))
    try:
        if client.status!=101: raise RuntimeError("handshake HTTP "+str(client.status))
        client.sock.settimeout(110)
        model=client.headers["x-vsr-realtime-provider-model"]
        if args.task=="speech":
            client.send({"type":"session.config","model":model,"voice":args.voice,"response_format":"wav","max_new_tokens":args.max_new_tokens})
            client.send({"type":"input.text","text":args.text});client.send({"type":"input.done"})
        else:
            print(json.dumps(client.event()),file=sys.stderr)
            client.send({"type":"session.update","model":model})
            with args.audio.open("rb") as stream:
                while chunk:=stream.read(16000): client.send({"type":"input_audio_buffer.append","audio":base64.b64encode(chunk).decode()})
            client.send({"type":"input_audio_buffer.commit","final":True})
        for _ in range(10000):
            opcode,payload=client.receive()
            if opcode==2: sys.stdout.buffer.write(payload);sys.stdout.buffer.flush();continue
            if opcode==8: break
            if opcode!=1: continue
            event=json.loads(payload);print(json.dumps(event),file=sys.stderr)
            if event["type"]=="error": raise RuntimeError("native engine rejected the event; see stderr")
            if args.task=="speech" and event["type"]=="session.done":
                client.send({"type":"session.close"});client.receive();break
            if args.task=="realtime" and event["type"]==("response.output_audio.done" if args.audio_output else "transcription.done"):
                client.close();break
        else: raise RuntimeError("native session did not complete within the example frame bound")
    finally: client.sock.close()
