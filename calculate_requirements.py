#!/usr/bin/env python3

import os
import re
import json
import argparse
import sys
from pathlib import Path
import urllib.parse
from typing import Dict, Set, List, Tuple


def find_markdown_links(content: str) -> List[str]:
  """Extract relative file links from markdown content."""
  # Match markdown links with relative paths (starting with ./ or ../)
  pattern = r'\[([^\]]*)\]\(([^)]+)\)'
  links = []
  
  for match in re.finditer(pattern, content):
    link_path = match.group(2)
    # Only include relative file links that reach up
    if link_path.startswith('../'):
      links.append(link_path)
  
  return links


def normalize_path(base_path: Path, relative_path: str) -> Path:
  """Resolve a relative path from a base path."""
  return (base_path / relative_path).resolve()


def get_relationship(target_dir: Path, linked_file: Path) -> str:
  """Determine the relationship between target directory and linked file."""
  try:
    # Check if linked file is internal to target directory
    linked_file.relative_to(target_dir)
    return "internal"
  except ValueError:
    pass
  
  # Check if linked file is a sibling (shares parent with target directory)
  target_parent = target_dir.parent
  try:
    linked_file.relative_to(target_parent)
    # If we can resolve relative to parent, it's either sibling or internal
    # We already know it's not internal, so it must be sibling
    return "sibling"
  except ValueError:
    # If we can't resolve relative to parent, it's external (cousin/grandparent)
    return "external"


def crawl_markdown_directory(directory: str) -> Tuple[Set[str], List[Tuple[str, str]]]:
  """
  Crawl markdown files in directory and categorize links.
  
  Returns:
    - Set of sibling file paths
    - List of (markdown_file, external_link) tuples for errors
  """
  target_dir = Path(directory).resolve()
  sibling_links = set()
  error_links = []
  
  # Find all markdown files recursively
  for md_file in target_dir.rglob("*.md"):
    try:
      with open(md_file, 'rt', encoding='utf-8') as f:
        content = f.read()
      
      links = find_markdown_links(content)
      
      for link in links:
        try:
          # Resolve the linked file path
          linked_file = normalize_path(md_file.parent, link)
          
          # Determine relationship
          relationship = get_relationship(target_dir, linked_file)
          
          if relationship == "internal":
            # Ignore internal links
            continue
          elif relationship == "sibling":
            # Add to sibling links set
            sibling_links.add(linked_file)
          elif relationship == "external":
            # Add to error list
            error_links.append((str(md_file), link))
            
        except Exception as e:
          error_links.append((str(md_file), f"{link} (Unexpected error: {e})"))
          
    except Exception as e:
      raise Exception(f"Error reading {md_file}: {e}")
  
  return sibling_links, error_links

def build_path_trie(paths: Set[Path], root_dir: Path) -> Dict[str, Dict]:
  """
  Build a trie (nested dict) of directory structure from a set of paths.
  
  Args:
    paths: Set of pathlib.Path objects
    root_dir: Root directory to make paths relative to
    
  Returns:
    Nested dictionary representing the directory structure (trie)
  """
  trie = {}
  for path in paths:
    # Make path relative to root_dir
    relative_path = path.relative_to(root_dir)
    
    # Get all parent directories (excluding the file itself)
    parts = relative_path.parts[:-1]  # Remove filename
    
    # Navigate/build the trie
    current = trie
    for part in parts:
      parsed_part = urllib.parse.unquote(part)
      if parsed_part not in current:
        current[parsed_part] = {}
      current = current[parsed_part]
  return trie


def main():
  parser = argparse.ArgumentParser(
    description="Crawl markdown files for relative links and categorize them"
  )
  parser.add_argument("directory", help="Directory to crawl for markdown files")
  parser.add_argument("filename", help="Output filename for JSON list of sibling links")
  
  args = parser.parse_args()
  
  # Validate directory exists
  if not os.path.isdir(args.directory):
    print(f"Error: Directory '{args.directory}' does not exist", file=sys.stderr)
    sys.exit(1)
  
  # Crawl the directory
  sibling_links, error_links = crawl_markdown_directory(args.directory)
  
  # Handle errors
  if error_links:
    print("Errors found parsing the links:", file=sys.stderr)
    for md_file, link in error_links:
      print(f"  {md_file}: {link}", file=sys.stderr)
    sys.exit(1)
  
  req_trie = build_path_trie(sibling_links, Path(args.directory).parent)
  
  # Write sibling links to JSON file
  try:
    with open(args.filename, 'w', encoding='utf-8') as f:
      json.dump(req_trie, f, indent=2, sort_keys=True)
    print(f"Found {len(sibling_links)} sibling links pointing to {len(req_trie)} unique module(s).")
  except Exception as e:
    print(f"Error writing to {args.filename}: {e}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
  main()
