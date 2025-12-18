"""
Function to group OME-TIFF image files by region identifier and extract channel/marker information.

This module provides functionality to:
1. Parse and group image files by region (R###)
2. Extract channel and marker information from filenames

Files follow the naming convention:
prefix_mmddyyyy_S#_[1-15].0.4_R###_(channel)_(marker)_FINAL_suffix.ome.tif
"""

import re
from pathlib import Path
from typing import Dict, List, Union
from collections import defaultdict


def group_ome_tiff_by_region(
    directory: Union[str, Path]
) -> Dict[str, List[str]]:
    """
    Group OME-TIFF files by their region identifier (R###).
    
    This function searches for files matching the specified naming convention
    and groups them by their region identifier. Only files containing 'FINAL'
    in their name are included.
    
    Parameters
    ----------
    directory : str or Path
        Path to the directory containing the OME-TIFF files
    
    Returns
    -------
    dict
        Dictionary with region IDs (e.g., "R001") as keys and lists of file 
        paths as values
    
    Examples
    --------
    >>> # Get groups as dictionary
    >>> groups = group_ome_tiff_by_region("/path/to/images")
    >>> print(groups.keys())
    dict_keys(['R000', 'R001', 'R002', ...])
    
    >>> # Access files for a specific region
    >>> r000_files = groups['R000']
    >>> print(f"Found {len(r000_files)} files")
    
    Notes
    -----
    The regex pattern matches files with this structure:
    - region: R followed by 3 digits (R000-R999) - **REQUIRED**
    - must contain 'FINAL' anywhere in filename - **REQUIRED**
    - extension: .ome.tif - **REQUIRED**
    
    All other parts of the filename (prefix, date, sample, round, channel, 
    marker, suffix) are ignored by the pattern, making it flexible for 
    various naming conventions as long as R###, FINAL, and .ome.tif are present.
    """
    
    # Convert to Path object for easier handling
    directory = Path(directory)
    
    if not directory.exists():
        raise ValueError(f"Directory does not exist: {directory}")
    
    if not directory.is_dir():
        raise ValueError(f"Path is not a directory: {directory}")
    
    # Simplified regex pattern using lookahead to match essential components
    # in any order:
    # - R### (region identifier with exactly 3 digits)
    # - FINAL (must be present in filename)
    # - .ome.tif (file extension)
    #
    # Pattern breakdown:
    # ^ : start of filename
    # (?=.*(R\d{3})) : lookahead to find and capture R### anywhere (includes R)
    # (?=.*FINAL) : lookahead to ensure FINAL exists anywhere
    # .* : match the entire filename
    # \.ome\.tif$ : must end with .ome.tif extension
    #
    # The lookaheads make the pattern order-independent
    
    pattern = re.compile(
        r'^(?=.*(R\d{3}))(?=.*FINAL).*\.ome\.tif$',
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
            # Extract the region identifier (only capture group)
            region_id = match.group(1)
            
            # Add the full file path to the corresponding region group
            region_groups[region_id].append(str(file_path))
    
    # Sort files within each group for consistent ordering
    for region_id in region_groups:
        region_groups[region_id].sort()
    
    # Return as regular dict (sorted by region ID)
    return dict(sorted(region_groups.items()))


def extract_channel_marker_info(
    directory: Union[str, Path]
) -> Dict[str, List[str]]:
    """
    Extract round, channel, and marker information organized by region.
    
    This function parses OME-TIFF filenames to extract imaging round numbers,
    channel names, and marker names, organizing them by region identifier.
    
    Parameters
    ----------
    directory : str or Path
        Path to the directory containing the OME-TIFF files
    
    Returns
    -------
    dict
        Dictionary with region IDs as keys and lists of channel/marker strings
        as values. Each string follows the format:
        - For DAPI: "round_DAPI" (e.g., "1.0.4_DAPI")
        - For other channels: "round_channel_marker" (e.g., "1.0.4_Cy3_iba1")
    
    Examples
    --------
    >>> info = extract_channel_marker_info("/path/to/images")
    >>> print(info)
    {
        'R000': ['1.0.4_DAPI', '1.0.4_Cy3_iba1', '1.0.4_Cy5_Neun', '1.0.4_FITC_GFAP'],
        'R001': ['1.0.4_DAPI', '1.0.4_Cy3_iba1', '1.0.4_Cy5_Neun'],
        ...
    }
    
    Notes
    -----
    The function expects two filename patterns:
    
    1. For DAPI files:
       prefix_mmddyyyy_S#_round_R###_DAPI_FINAL_F.ome.tif
       
    2. For other channels:
       prefix_mmddyyyy_S#_round_R###_channel_marker_FINAL_AFR_F.ome.tif
    
    Where:
    - round: format like 1.0.4, 2.0.1, etc. (can be 1-15 for first number)
    - R###: region identifier (e.g., R000, R001)
    - channel: DAPI, Cy3, Cy5, FITC, or Cy7
    - marker: alphanumeric name (not present for DAPI)
    """
    
    # Convert to Path object
    directory = Path(directory)
    
    if not directory.exists():
        raise ValueError(f"Directory does not exist: {directory}")
    
    if not directory.is_dir():
        raise ValueError(f"Path is not a directory: {directory}")
    
    # Pattern for DAPI files (no marker)
    # Format: prefix_date_sample_round_region_DAPI_FINAL_F.ome.tif
    dapi_pattern = re.compile(
        r'^.+?_'                    # prefix
        r'\d{8}_'                   # date (mmddyyyy)
        r'S\d{1,2}_'                # sample (S1-S15)
        r'(\d{1,2}\.\d+\.\d+)_'     # round (captured) - e.g., 1.0.4
        r'(R\d{3})_'                # region (captured)
        r'DAPI_'                    # DAPI channel
        r'.*FINAL.*'                # must contain FINAL
        r'\.ome\.tif$',             # extension
        re.IGNORECASE
    )
    
    # Pattern for non-DAPI files (with marker)
    # Format: prefix_date_sample_round_region_channel_marker_FINAL_AFR_F.ome.tif
    channel_marker_pattern = re.compile(
        r'^.+?_'                    # prefix
        r'\d{8}_'                   # date (mmddyyyy)
        r'S\d{1,2}_'                # sample (S1-S15)
        r'(\d{1,2}\.\d+\.\d+)_'     # round (captured) - e.g., 1.0.4
        r'(R\d{3})_'                # region (captured)
        r'(Cy3|Cy5|FITC|Cy7)_'      # channel (captured)
        r'([^_]+)_'                 # marker (captured) - anything except underscore
        r'.*FINAL.*'                # must contain FINAL
        r'\.ome\.tif$',             # extension
        re.IGNORECASE
    )
    
    # Dictionary to store channel/marker info by region
    region_info = defaultdict(list)
    
    # Iterate through all files in the directory
    for file_path in directory.iterdir():
        # Skip if not a file
        if not file_path.is_file():
            continue
        
        filename = file_path.name
        
        # Try matching DAPI pattern first
        dapi_match = dapi_pattern.match(filename)
        if dapi_match:
            round_num = dapi_match.group(1)
            region_id = dapi_match.group(2)
            info_string = f"{round_num}_DAPI"
            region_info[region_id].append(info_string)
            continue
        
        # Try matching channel+marker pattern
        channel_match = channel_marker_pattern.match(filename)
        if channel_match:
            round_num = channel_match.group(1)
            region_id = channel_match.group(2)
            channel = channel_match.group(3)
            marker = channel_match.group(4)
            info_string = f"{round_num}_{channel}_{marker}"
            region_info[region_id].append(info_string)
    
    # Sort the info strings within each region for consistent ordering
    for region_id in region_info:
        region_info[region_id].sort()
    
    # Return as regular dict (sorted by region ID)
    return dict(sorted(region_info.items()))


def print_group_summary(groups: Dict[str, List[str]]) -> None:
    """
    Print a summary of the grouped files.
    
    Parameters
    ----------
    groups : dict
        The output from group_ome_tiff_by_region()
    """
    print(f"Found {len(groups)} region groups:")
    for region_id, files in groups.items():
        print(f"\n{region_id}: {len(files)} files")
        for file_path in files:
            print(f"  - {Path(file_path).name}")


def print_channel_marker_info(info: Dict[str, List[str]]) -> None:
    """
    Print a summary of the channel and marker information.
    
    Parameters
    ----------
    info : dict
        The output from extract_channel_marker_info()
    """
    print(f"Found channel/marker info for {len(info)} regions:")
    for region_id, channel_list in info.items():
        print(f"\n{region_id}: {len(channel_list)} channels")
        for channel_info in channel_list:
            print(f"  - {channel_info}")


# Example usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    else:
        directory = "/mnt/user-data/uploads"  # Default to uploaded files
    
    print(f"Searching for OME-TIFF files in: {directory}\n")
    
    try:
        # Get groups as dictionary
        groups_dict = group_ome_tiff_by_region(directory)
        print_group_summary(groups_dict)
        
        print("\n" + "="*60)
        print("\nExample: Accessing files from a specific region:")
        if groups_dict:
            first_region = list(groups_dict.keys())[0]
            print(f"\nFiles in region {first_region}:")
            for file_path in groups_dict[first_region]:
                print(f"  {Path(file_path).name}")
        
        print("\n" + "="*60)
        print("\nExtracting channel and marker information:")
        channel_marker_info = extract_channel_marker_info(directory)
        print_channel_marker_info(channel_marker_info)
        
        print("\n" + "="*60)
        print("\nExample: Accessing channel/marker info for a specific region:")
        if channel_marker_info:
            first_region = list(channel_marker_info.keys())[0]
            print(f"\nChannel/Marker info for region {first_region}:")
            for info in channel_marker_info[first_region]:
                print(f"  {info}")
        
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")