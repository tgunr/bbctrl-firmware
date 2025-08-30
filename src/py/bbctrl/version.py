################################################################################
#                                                                              #
#                 This file is part of the Buildbotics firmware.               #
#                                                                              #
#        Copyright (c) 2015 - 2023, Buildbotics LLC, All rights reserved.      #
#                                                                              #
#         This Source describes Open Hardware and is licensed under the        #
#                                 CERN-OHL-S v2.                               #
#                                                                              #
#         You may redistribute and modify this Source and make products        #
#    using it under the terms of the CERN-OHL-S v2 (https:/cern.ch/cern-ohl).  #
#           This Source is distributed WITHOUT ANY EXPRESS OR IMPLIED          #
#    WARRANTY, INCLUDING OF MERCHANTABILITY, SATISFACTORY QUALITY AND FITNESS  #
#     FOR A PARTICULAR PURPOSE. Please see the CERN-OHL-S v2 for applicable    #
#                                  conditions.                                 #
#                                                                              #
#                Source location: https://github.com/buildbotics               #
#                                                                              #
#      As per CERN-OHL-S v2 section 4, should You produce hardware based on    #
#    these sources, You must maintain the Source Location clearly visible on   #
#    the external case of the CNC Controller or other product you make using   #
#                                  this Source.                                #
#                                                                              #
#                For more information, email info@buildbotics.com              #
#                                                                              #
################################################################################

import re
from typing import Optional, Tuple, List, Union


class Version:
    """
    Semantic Version class following SemVer specification with custom pre-release identifiers.

    Format: MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]
    Pre-release identifiers: dev, alpha, beta, rc
    """

    # Valid pre-release identifiers in order of precedence (lowest to highest)
    PRERELEASE_IDENTIFIERS = ['dev', 'alpha', 'beta', 'rc']

    # Regex pattern for SemVer validation (supports both - and . for prerelease, and build numbers)
    SEMVER_PATTERN = re.compile(
        r'^(\d+)\.(\d+)\.(\d+)'  # MAJOR.MINOR.PATCH
        r'([-.]([a-zA-Z0-9]+(?:\.[a-zA-Z0-9]+)*))?'  # [-|.]PRERELEASE
        r'(-(\d+))?'  # [-BUILDNUMBER]
        r'(\+([a-zA-Z0-9](?:\.[a-zA-Z0-9]+)*))?'  # [+BUILD]
        r'$'
    )

    def __init__(self, version_string: str):
        """
        Initialize Version object from version string.

        Args:
            version_string: Version string in SemVer format

        Raises:
            ValueError: If version string is invalid
        """
        self.version_string = version_string
        self.major, self.minor, self.patch = 0, 0, 0
        self.prerelease: Optional[str] = None
        self.build_number: Optional[int] = None
        self.build: Optional[str] = None

        self._parse(version_string)

    def _parse(self, version_string: str) -> None:
        """Parse version string and validate format."""
        match = self.SEMVER_PATTERN.match(version_string)
        if not match:
            raise ValueError(f"Invalid version format: {version_string}")

        self.major = int(match.group(1))
        self.minor = int(match.group(2))
        self.patch = int(match.group(3))

        if match.group(4):  # Has prerelease
            self.prerelease = match.group(5)

        if match.group(6):  # Has build number
            self.build_number = int(match.group(7))

        if match.group(8):  # Has build metadata
            self.build = match.group(9)

        self._validate_prerelease()

    def _validate_prerelease(self) -> None:
        """Validate prerelease identifier format."""
        if not self.prerelease:
            return

        # Check if it starts with valid identifier or is a valid single identifier
        parts = self.prerelease.split('.')

        # Check first part
        first_part = parts[0]
        if not first_part:
            raise ValueError(f"Invalid prerelease identifier: empty first part")

        # Check if it's a known identifier (dev, alpha, beta, rc) optionally followed by digits
        if first_part in self.PRERELEASE_IDENTIFIERS:
            # Valid known identifier, check if there's a numeric part
            pass
        else:
            # Check if it's a single identifier like "dev3", "alpha1", etc.
            for identifier in self.PRERELEASE_IDENTIFIERS:
                if first_part.startswith(identifier):
                    remaining = first_part[len(identifier):]
                    if remaining.isdigit():
                        # Valid format like "dev3", "alpha1"
                        break
            else:
                # Check if the whole first part is just a known identifier
                if first_part not in self.PRERELEASE_IDENTIFIERS:
                    raise ValueError(f"Invalid prerelease identifier: {first_part}")

        # Validate remaining parts
        for part in parts[1:]:
            if not part:
                raise ValueError(f"Invalid prerelease identifier: empty part in {self.prerelease}")
            # Each part after the first should be numeric or another valid identifier
            if not (part.isdigit() or part in self.PRERELEASE_IDENTIFIERS):
                # Allow alphanumeric combinations for complex identifiers
                if not part.replace('_', '').replace('-', '').isalnum():
                    raise ValueError(f"Invalid prerelease identifier part: {part}")

    @classmethod
    def parse(cls, version_string: str) -> 'Version':
        """Parse version string and return Version object."""
        return cls(version_string)

    @classmethod
    def is_valid(cls, version_string: str) -> bool:
        """Check if version string is valid SemVer format."""
        try:
            cls(version_string)
            return True
        except ValueError:
            return False

    def __str__(self) -> str:
        """Return version string."""
        return self.version_string

    def __repr__(self) -> str:
        """Return string representation."""
        return f"Version('{self.version_string}')"

    def __eq__(self, other: object) -> bool:
        """Check equality with another Version."""
        if not isinstance(other, Version):
            return NotImplemented
        return self.version_string == other.version_string

    def __lt__(self, other: 'Version') -> bool:
        """Compare versions for less than."""
        return self._compare(other) < 0

    def __le__(self, other: 'Version') -> bool:
        """Compare versions for less than or equal."""
        return self._compare(other) <= 0

    def __gt__(self, other: 'Version') -> bool:
        """Compare versions for greater than."""
        return self._compare(other) > 0

    def __ge__(self, other: 'Version') -> bool:
        """Compare versions for greater than or equal."""
        return self._compare(other) >= 0

    def _compare(self, other: 'Version') -> int:
        """
        Compare this version with another version.

        Returns:
            -1 if self < other
             0 if self == other
             1 if self > other
        """
        # Compare major.minor.patch
        for self_part, other_part in [(self.major, other.major),
                                     (self.minor, other.minor),
                                     (self.patch, other.patch)]:
            if self_part != other_part:
                return (self_part > other_part) - (self_part < other_part)

        # Compare prerelease
        if self.prerelease and not other.prerelease:
            return -1  # Prerelease < final release
        elif not self.prerelease and other.prerelease:
            return 1   # Final release > prerelease
        elif self.prerelease and other.prerelease:
            prerelease_cmp = self._compare_prerelease(other.prerelease)
            if prerelease_cmp != 0:
                return prerelease_cmp

        # Compare build numbers (only if both have them)
        if self.build_number is not None and other.build_number is not None:
            if self.build_number != other.build_number:
                return (self.build_number > other.build_number) - (self.build_number < other.build_number)
        elif self.build_number is not None:
            return 1  # Version with build number > version without
        elif other.build_number is not None:
            return -1  # Version without build number < version with

        return 0  # Equal

    def _compare_prerelease(self, other_prerelease: str) -> int:
        """Compare prerelease identifiers."""
        self_parts = self.prerelease.split('.')
        other_parts = other_prerelease.split('.')

        # Extract base identifier and numeric part for each
        def parse_identifier_part(part: str) -> tuple[str, int]:
            for identifier in self.PRERELEASE_IDENTIFIERS:
                if part.startswith(identifier):
                    remaining = part[len(identifier):]
                    if remaining.isdigit():
                        return identifier, int(remaining)
                    elif not remaining:
                        return identifier, 0
            # If no match, treat as unknown identifier with precedence after all known ones
            return part, 0

        self_base, self_num = parse_identifier_part(self_parts[0])
        other_base, other_num = parse_identifier_part(other_parts[0])

        # Compare identifier precedence
        try:
            self_idx = self.PRERELEASE_IDENTIFIERS.index(self_base)
        except ValueError:
            self_idx = len(self.PRERELEASE_IDENTIFIERS)  # Unknown identifiers come last

        try:
            other_idx = self.PRERELEASE_IDENTIFIERS.index(other_base)
        except ValueError:
            other_idx = len(self.PRERELEASE_IDENTIFIERS)  # Unknown identifiers come last

        if self_idx != other_idx:
            return (self_idx > other_idx) - (self_idx < other_idx)

        # Same identifier type, compare numeric parts
        if self_num != other_num:
            return (self_num > other_num) - (self_num < other_num)

        # If we have more parts, compare them lexicographically
        self_remaining = '.'.join(self_parts[1:])
        other_remaining = '.'.join(other_parts[1:])

        if self_remaining != other_remaining:
            return (self_remaining > other_remaining) - (self_remaining < other_remaining)

        return 0

    def is_prerelease(self) -> bool:
        """Check if this is a prerelease version."""
        return self.prerelease is not None

    def is_development(self) -> bool:
        """Check if this is a development release."""
        return self.prerelease and self.prerelease.startswith('dev')

    def is_alpha(self) -> bool:
        """Check if this is an alpha release."""
        return self.prerelease and self.prerelease.startswith('alpha')

    def is_beta(self) -> bool:
        """Check if this is a beta release."""
        return self.prerelease and self.prerelease.startswith('beta')

    def is_release_candidate(self) -> bool:
        """Check if this is a release candidate."""
        return self.prerelease and self.prerelease.startswith('rc')

    def get_stage(self) -> str:
        """Get the development stage of this version."""
        if not self.is_prerelease():
            return 'final'
        elif self.is_development():
            return 'development'
        elif self.is_alpha():
            return 'alpha'
        elif self.is_beta():
            return 'beta'
        elif self.is_release_candidate():
            return 'release-candidate'
        else:
            return 'unknown'

    def bump_major(self) -> 'Version':
        """Return new version with major bumped."""
        return Version(f"{self.major + 1}.0.0")

    def bump_minor(self) -> 'Version':
        """Return new version with minor bumped."""
        return Version(f"{self.major}.{self.minor + 1}.0")

    def bump_patch(self) -> 'Version':
        """Return new version with patch bumped."""
        return Version(f"{self.major}.{self.minor}.{self.patch + 1}")

    def bump_prerelease(self) -> 'Version':
        """Return new version with prerelease bumped."""
        if not self.prerelease:
            raise ValueError("Cannot bump prerelease on final version")

        parts = self.prerelease.split('.')

        # Parse the first part to extract base identifier and number
        first_part = parts[0]
        for identifier in self.PRERELEASE_IDENTIFIERS:
            if first_part.startswith(identifier):
                remaining = first_part[len(identifier):]
                if remaining.isdigit():
                    # Format like "dev3" - bump the number
                    num = int(remaining) + 1
                    return Version(f"{self.major}.{self.minor}.{self.patch}-{identifier}{num}")
                elif not remaining:
                    # Check if we have a dot-separated number (e.g., "dev.4")
                    if len(parts) == 2 and parts[1].isdigit():
                        num = int(parts[1]) + 1
                        return Version(f"{self.major}.{self.minor}.{self.patch}-{identifier}.{num}")
                    else:
                        # Format like "dev" - add .1
                        return Version(f"{self.major}.{self.minor}.{self.patch}-{identifier}1")

        # If no known identifier found, append .1 to the whole thing
        return Version(f"{self.major}.{self.minor}.{self.patch}-{first_part}.1")

    def to_final(self) -> 'Version':
        """Return final version (without prerelease)."""
        return Version(f"{self.major}.{self.minor}.{self.patch}")

    def next_stage(self) -> 'Version':
        """Move to next development stage."""
        if self.is_development():
            return Version(f"{self.major}.{self.minor}.{self.patch}-alpha.1")
        elif self.is_alpha():
            return Version(f"{self.major}.{self.minor}.{self.patch}-beta.1")
        elif self.is_beta():
            return Version(f"{self.major}.{self.minor}.{self.patch}-rc.1")
        elif self.is_release_candidate():
            return Version(f"{self.major}.{self.minor}.{self.patch}")
        else:
            # Final version - bump minor for next development cycle
            return Version(f"{self.major}.{self.minor + 1}.0-dev.1")

    def with_build(self, build: str) -> 'Version':
        """Return version with build metadata."""
        base = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            base += f"-{self.prerelease}"
        return Version(f"{base}+{build}")


def parse_version(version_string: str) -> Version:
    """Parse version string and return Version object."""
    return Version.parse(version_string)


def compare_versions(version1: str, version2: str) -> int:
    """
    Compare two version strings.

    Returns:
        -1 if version1 < version2
         0 if version1 == version2
         1 if version1 > version2
    """
    v1 = Version(version1)
    v2 = Version(version2)
    return v1._compare(v2)


def version_less(version1: str, version2: str) -> bool:
    """Check if version1 is less than version2."""
    return compare_versions(version1, version2) < 0


__all__ = ['Version', 'parse_version', 'compare_versions', 'version_less']