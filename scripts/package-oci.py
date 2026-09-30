#!/usr/bin/env python3
"""Append the native build to a locked OCI base; no Docker daemon required.

Accepts a containerd OCI export, verifies all retained content, creates a
deterministic replacement layer and a single-platform OCI archive. This does
not execute a Dockerfile or assert acceptance; the resulting digest must be
tested and recorded separately. https://github.com/opencontainers/image-spec
"""
import argparse
import copy
import gzip
import hashlib
import io
import json
from pathlib import Path
import shutil
import tarfile
import tempfile


def json_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def digest(data):
    return "sha256:" + hashlib.sha256(data).hexdigest()


def blob_path(value):
    algorithm, encoded = value.split(":", 1)
    if algorithm != "sha256" or len(encoded) != 64 or any(c not in "0123456789abcdef" for c in encoded):
        raise ValueError("only valid sha256 descriptors are accepted")
    return "blobs/sha256/" + encoded


def descriptor(data, media_type):
    return {"mediaType": media_type, "digest": digest(data), "size": len(data)}


def add_bytes(archive, name, data, mode=0o644):
    info = tarfile.TarInfo(name)
    info.size, info.mode, info.mtime = len(data), mode, 0
    archive.addfile(info, io.BytesIO(data))


def package(args):
    platform_os, architecture = args.platform.split("/")
    with tarfile.open(args.base, "r:*") as base, tempfile.TemporaryDirectory(dir=args.output.parent) as tmp:
        def read_json(desc):
            data = base.extractfile(blob_path(desc["digest"])).read()
            if digest(data) != desc["digest"] or len(data) != desc["size"]:
                raise ValueError("invalid base descriptor")
            return json.loads(data)

        index = json.load(base.extractfile("index.json"))
        locked = [d for d in index["manifests"] if d["digest"] == args.base_digest]
        if len(locked) != 1:
            raise ValueError("base export does not contain exactly the locked base reference")

        def select(desc):
            document = read_json(desc)
            if "manifests" in document:
                candidates = [d for d in document["manifests"]
                              if d.get("platform", {}).get("os") == platform_os
                              and d.get("platform", {}).get("architecture") == architecture]
                if len(candidates) != 1:
                    raise ValueError("base platform is unavailable or ambiguous")
                return select(candidates[0])
            config = read_json(document["config"])
            if (config.get("os"), config.get("architecture")) != (platform_os, architecture):
                raise ValueError("base image does not match the requested platform")
            return document, config

        manifest, config = select(locked[0])
        layer_path = Path(tmp) / "layer.tar"
        with tarfile.open(layer_path, "w", format=tarfile.PAX_FORMAT) as layer:
            data = args.binary.read_bytes()
            binary_digest = digest(data)
            add_bytes(layer, "app/router-candle", data, 0o755)
            for name in ["app/router-onnx", "app/router-openvino"]:
                info = tarfile.TarInfo(name)
                info.type, info.linkname, info.mode = tarfile.LNKTYPE, "app/router-candle", 0o755
                layer.addfile(info)
            add_bytes(layer, "app/share/router-config-v0.3.schema.json", args.schema.read_bytes())
        with layer_path.open("rb") as source:
            diff_id = "sha256:" + hashlib.file_digest(source, "sha256").hexdigest()
        compressed_path = Path(tmp) / "layer.tar.gz"
        with layer_path.open("rb") as source, compressed_path.open("wb") as target:
            with gzip.GzipFile(filename="", mode="wb", fileobj=target, mtime=0) as compressed:
                shutil.copyfileobj(source, compressed)
        with compressed_path.open("rb") as source:
            layer_digest = "sha256:" + hashlib.file_digest(source, "sha256").hexdigest()
        new_config = copy.deepcopy(config)
        new_config["config"]["Entrypoint"] = ["/app/router-candle"]
        new_config["config"]["Cmd"] = []
        new_config["config"].setdefault("Labels", {}).update({
            "org.opencontainers.image.revision": args.commit,
            "org.opencontainers.image.base.digest": args.base_digest,
            "org.semantic-router.multimodal.patch-sha256": args.patch_digest,
            "org.semantic-router.multimodal.binary-sha256": binary_digest,
        })
        new_config["rootfs"]["diff_ids"].append(diff_id)
        new_config.setdefault("history", []).append({"created_by": "semantic-router-multimodal package-oci.py"})
        new_config_bytes = json_bytes(new_config)
        new_manifest = copy.deepcopy(manifest)
        new_manifest["mediaType"] = "application/vnd.oci.image.manifest.v1+json"
        new_manifest["config"] = descriptor(new_config_bytes, "application/vnd.oci.image.config.v1+json")
        new_manifest["layers"].append({"mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                                       "digest": layer_digest, "size": compressed_path.stat().st_size})
        new_manifest_bytes = json_bytes(new_manifest)
        output_descriptor = descriptor(new_manifest_bytes, new_manifest["mediaType"])
        output_descriptor["platform"] = {"os": platform_os, "architecture": architecture}
        output_descriptor["annotations"] = {"org.opencontainers.image.ref.name": args.reference,
                                            "io.containerd.image.name": args.reference}
        output_index = {"schemaVersion": 2, "mediaType": "application/vnd.oci.image.index.v1+json",
                        "manifests": [output_descriptor]}
        temp_output = args.output.with_suffix(".tmp")
        with tarfile.open(temp_output, "w", format=tarfile.PAX_FORMAT) as output:
            add_bytes(output, "oci-layout", json_bytes({"imageLayoutVersion": "1.0.0"}))
            add_bytes(output, "index.json", json_bytes(output_index))
            for retained in manifest["layers"]:
                path = blob_path(retained["digest"])
                with base.extractfile(path) as source:
                    if "sha256:" + hashlib.file_digest(source, "sha256").hexdigest() != retained["digest"]:
                        raise ValueError("base layer checksum mismatch")
                info = tarfile.TarInfo(path)
                info.size = retained["size"]
                with base.extractfile(path) as source:
                    output.addfile(info, source)
            add_bytes(output, blob_path(digest(new_config_bytes)), new_config_bytes)
            add_bytes(output, blob_path(digest(new_manifest_bytes)), new_manifest_bytes)
            info = tarfile.TarInfo(blob_path(layer_digest))
            info.size = compressed_path.stat().st_size
            with compressed_path.open("rb") as source:
                output.addfile(info, source)
        temp_output.replace(args.output)
        result = {"reference": args.reference.rsplit(":", 1)[0] + "@" + output_descriptor["digest"],
                  "tag": args.reference, "digest": output_descriptor["digest"], "platform": args.platform,
                  "config_digest": new_manifest["config"]["digest"],
                  "base_digest": args.base_digest, "binary_digest": binary_digest,
                  "patch_digest": args.patch_digest, "upstream_commit": args.commit,
                  "build_method": args.build_method, "acceptance": "pending"}
        args.output.with_suffix(".json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ["base", "binary", "schema", "output"]:
        parser.add_argument("--" + option, type=Path, required=True)
    for option in ["base-digest", "platform", "reference", "commit", "patch-digest"]:
        parser.add_argument("--" + option, required=True)
    parser.add_argument("--build-method", default="native-cgo-build-plus-verified-oci-layer",
                        choices=["native-cgo-build-plus-verified-oci-layer", "cross-cgo-qemu-tests-plus-verified-oci-layer"])
    arguments = parser.parse_args()
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    package(arguments)
