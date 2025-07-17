#!/usr/bin/env python
import argparse
import yaml, json, os

parser = argparse.ArgumentParser(
  description="Creates the ./manifest.vnm file.",
)
parser.add_argument("path", help="Path to the module folder")
parser.add_argument(
  "--metadata",
  help="Path to the metadata yaml file. Defaults to $path/metadata.yaml",
  nargs="?",
  default=None
)
parser.add_argument(
  "--repo",
  help="The username/reponame for the current GitHub Repository",
)
parser.add_argument("--version", help="The released version (without the v).")
args = parser.parse_args()

assert len(args.version) >= 5, f"Got short version \"{args.version}\""
metadata_path = args.metadata
if not metadata_path:
  metadata_path = args.path + "/metadata.yaml"
metadata = yaml.safe_load(open(metadata_path, 'r'))
requires_path = os.environ["MY_WORKING_DIR"] + "/requires.json"
requires = json.load(open(requires_path, 'r'))
vnm_data = {
  "folder": metadata["folder"],
  "description": metadata.get("description"),
  "more_info": "https://github.com/" + args.repo,
  "version": args.version,
  "requires": requires,
  "zip": f"https://github.com/{ args.repo }/releases/download/v{args.version}/content.zip"
}
if ("submodules" in metadata):
  vnm_data["submodules"] = metadata["submodules"]
json.dump(vnm_data, open("./manifest.vnm", "w"), indent=2)