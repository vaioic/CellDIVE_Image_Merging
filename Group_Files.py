"""
Function to group OME-TIFF image files by region identifier.

This module provides functionality to parse and group image files following
the naming convention:
prefix_mmddyyyy_S#_[1-15].0.4_R###_(channel)_(marker)_FINAL_suffix.ome.tif
"""
import re
from pathlib import Path
from typing import Dict, List, Union
from collections import defaultdict

def group_ome_tiff_by_region(
    directory: Union[str, Path],
    return_type: str = "dict"
) -> Union[Dict[str, List[str]], List[List[str]]]:
    """
    Group OME-TIFF files by their region identifier (R###).
    
    This function searches for files matching the specified naming convention
    and groups them by their region identifier. Only files containing 'FINAL'
    in their name are included.
    
    Parameters
    ----------
    directory : str or Path
        Path to the directory containing the OME-TIFF files
    return_type : str, optional
        Format of the return value. Either "dict" (default) or "list"
        - "dict": Returns a dictionary with region IDs as keys
        - "list": Returns a list of lists, one per region
    
    Returns
    -------
    dict or list
        If return_type="dict": Dictionary with region IDs (e.g., "R001") as keys
            and lists of file paths as values
        If return_type="list": List of lists, where each inner list contains
            file paths for one region
    
    Examples
    --------
    >>> # Get groups as dictionary
    >>> groups = group_ome_tiff_by_region("/path/to/images", return_type="dict")
    >>> print(groups.keys())
    dict_keys(['R000', 'R001', 'R002', ...])
    
    >>> # Get groups as list of lists
    >>> groups = group_ome_tiff_by_region("/path/to/images", return_type="list")
    >>> print(f"Found {len(groups)} regions")
    Found 8 regions
    
    Notes
    -----
    The regex pattern matches files with this structure:
    - prefix: any characters (typically initials)
    - date: mmddyyyy format
    - sample: S followed by 1-2 digits (S1-S15)
    - round: integer 1-15, followed by .0.4
    - region: R followed by 3 digits (R000-R999)
    - channel: DAPI, Cy3, Cy5, FITC, or Cy7
    - marker: alphanumeric name
    - must contain 'FINAL'
    - suffix: AFR_F or _F
    - extension: .ome.tif
    """
    
    # Convert to Path object for easier handling
    directory = Path(directory)
    
    if not directory.exists():
        raise ValueError(f"Directory does not exist: {directory}")
    
    if not directory.is_dir():
        raise ValueError(f"Path is not a directory: {directory}")
    
    # Regex pattern to match the file naming convention
    # Pattern breakdown:
    # ^(.+?)_ : prefix (non-greedy) followed by underscore
    # (\d{8})_ : date in mmddyyyy format
    # (S\d{1,2})_ : sample ID (S1 to S15)
    # (\d{1,2}\.0\.\d+)_ : round number (1-15.0.4)
    # (R\d{3})_ : region identifier (R###)
    # (DAPI|Cy3|Cy5|FITC|Cy7)_ : channel name
    # ([A-Za-z0-9_]+)_ : marker name
    # .*FINAL.* : must contain FINAL
    # (AFR_F|_F) : suffix
    # \.ome\.tif$ : file extension
    
    pattern = re.compile(
        r'^(.+?)_'           # prefix
        r'(\d{8})_'          # date (mmddyyyy)
        r'(S\d{1,2})_'       # sample ID (S1-S15)
        r'(\d{1,2}\.\d+\.\d+)_'  # round (e.g., 1.0.1, 1.0.4, 15.0.4)
        r'(R\d{3})_'         # region (R###)
        r'(DAPI_|Cy3|Cy5|FITC|Cy7|FITC)_'  # channel name
        r'(.+?)_'            # marker name (non-greedy)
        r'.*FINAL.*'         # must contain FINAL
        r'(AFR_F|_F)'        # suffix
        r'\.ome\.tif$',      # extension
        re.IGNORECASE
    )
    
    # Dictionary to store grouped files
    region_groups = defaultdict(list)
    
    # Iterate through all files in the directory
    for file_path in directory.iterdir():
        # Skip if not a file
        if not file_path.is_file():
            continue
        
        filename = file_path.name
        
        # Check if filename matches the pattern
        match = pattern.match(filename)
        
        if match:
            # Extract the region identifier (5th capture group)
            region_id = match.group(5)
            
            # Add the full file path to the corresponding region group
            region_groups[region_id].append(str(file_path))
    
    # Sort files within each group for consistent ordering
    for region_id in region_groups:
        region_groups[region_id].sort()
    
    # Return based on requested format
    if return_type == "dict":
        # Return as regular dict (sorted by region ID)
        return dict(sorted(region_groups.items()))
    elif return_type == "list":
        # Return as list of lists (sorted by region ID)
        return [region_groups[region_id] for region_id in sorted(region_groups.keys())]
    else:
        raise ValueError(f"Invalid return_type: {return_type}. Must be 'dict' or 'list'")


def print_group_summary(groups: Union[Dict[str, List[str]], List[List[str]]]) -> None:
    """
    Print a summary of the grouped files.
    
    Parameters
    ----------
    groups : dict or list
        The output from group_ome_tiff_by_region()
    """
    if isinstance(groups, dict):
        print(f"Found {len(groups)} region groups:")
        for region_id, files in groups.items():
            print(f"\n{region_id}: {len(files)} files")
            for file_path in files:
                print(f"  - {Path(file_path).name}")
    elif isinstance(groups, list):
        print(f"Found {len(groups)} region groups:")
        for i, files in enumerate(groups):
            print(f"\nGroup {i+1}: {len(files)} files")
            for file_path in files:
                print(f"  - {Path(file_path).name}")
