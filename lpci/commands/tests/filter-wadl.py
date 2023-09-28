#! /usr/bin/python3
# Copyright 2023 Canonical Ltd.  This software is licensed under the
# GNU General Public License version 3 (see the file LICENSE).

"""
Make a filtered version of Launchpad's WADL description.

Download Launchpad's WADL description and filter it to include only the
parts we need.
"""

from pathlib import Path
from xml.etree import ElementTree

import requests

wadl_namespace = "http://research.sun.com/wadl/2006/10"

keep_collections = {
    "archives": ["getByReference"],
    "git_repositories": ["getByPath"],
}

keep_entries = {
    "archive": ["uploadCIBuild"],
    "ci_build": ["arch_tag", "buildstate", "datebuilt", "get"],
    "git_ref": ["commit_sha1", "get"],
    "git_repository": ["getRefByPath", "getStatusReports"],
    "revision_status_report": [
        "ci_build_link",
        "get",
        "getArtifactURLs",
        "page-resource-get",
    ],
}


def download_wadl() -> str:
    response = requests.get(
        "https://api.launchpad.net/devel/",
        headers={"Accept": "application/vnd.sun.wadl+xml"},
    )
    response.raise_for_status()
    return response.text


def reduce_wadl(wadl: str) -> ElementTree.Element:
    ElementTree.register_namespace("wadl", wadl_namespace)
    parsed = ElementTree.fromstring(wadl)

    for resource_type in parsed.findall(
        "wadl:resource_type", namespaces={"wadl": wadl_namespace}
    ):
        resource_type_name = resource_type.get("id")
        assert resource_type_name is not None
        if resource_type_name == "service-root":
            continue
        elif resource_type_name in keep_collections:
            keep_methods = [
                f"{resource_type_name}-{method}"
                for method in keep_collections[resource_type_name]
            ]
            for method in resource_type.findall(
                "wadl:method", namespaces={"wadl": wadl_namespace}
            ):
                if method.get("id") not in keep_methods:
                    resource_type.remove(method)
        elif resource_type_name in keep_entries:
            keep_methods = [
                f"{resource_type_name}-{method}"
                for method in keep_entries[resource_type_name]
            ]
            for method in resource_type.findall(
                "wadl:method", namespaces={"wadl": wadl_namespace}
            ):
                if method.get("id") not in keep_methods:
                    resource_type.remove(method)
        elif (
            resource_type_name.endswith("-page-resource")
            and resource_type_name[: -len("-page-resource")] in keep_entries
        ):
            continue
        else:
            parsed.remove(resource_type)

    for representation in parsed.findall(
        "wadl:representation", namespaces={"wadl": wadl_namespace}
    ):
        representation_name = representation.get("id")
        assert representation_name is not None
        if representation_name.endswith("-full"):
            representation_name = representation_name[: -len("-full")]
        if representation_name == "service-root-json":
            for collection_link_param in list(representation):
                collection_name = collection_link_param.get("name")
                assert collection_name is not None
                if collection_name.endswith("_collection_link"):
                    collection_name = collection_name[
                        : -len("_collection_link")
                    ]
                if collection_name not in keep_collections:
                    representation.remove(collection_link_param)
        elif representation_name in keep_entries:
            for param in representation.findall(
                "wadl:param", namespaces={"wadl": wadl_namespace}
            ):
                if param.get("name") in {
                    "http_etag",
                    "resource_type_link",
                    "self_link",
                    "web_link",
                }:
                    continue
                elif (
                    param.get("name") not in keep_entries[representation_name]
                ):
                    representation.remove(param)
        elif (
            representation_name.endswith("-page")
            and representation_name[: -len("-page")] in keep_entries
        ):
            continue
        else:
            parsed.remove(representation)

    return parsed


def write_wadl(parsed: ElementTree.Element, path: Path) -> None:
    ElementTree.ElementTree(parsed).write(path, xml_declaration=True)


write_wadl(
    reduce_wadl(download_wadl()), Path(__file__).parent / "launchpad-wadl.xml"
)
