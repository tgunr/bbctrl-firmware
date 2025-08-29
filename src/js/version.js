/******************************************************************************\

                   This file is part of the Buildbotics firmware.

          Copyright (c) 2015 - 2023, Buildbotics LLC, All rights reserved.

           This Source describes Open Hardware and is licensed under the
                                   CERN-OHL-S v2.

           You may redistribute and modify this Source and make products
      using it under the terms of the CERN-OHL-S v2 (https:/cern.ch/cern-ohl).
             This Source is distributed WITHOUT ANY EXPRESS OR IMPLIED
      WARRANTY, INCLUDING OF MERCHANTABILITY, SATISFACTORY QUALITY AND FITNESS
       FOR A PARTICULAR PURPOSE. Please see the CERN-OHL-S v2 for applicable
                                    conditions.

                  Source location: https://github.com/buildbotics

        As per CERN-OHL-S v2 section 4, should You produce hardware based on
      these sources, You must maintain the Source Location clearly visible on
      the external case of the CNC Controller or other product you make using
                                    this Source.

                  For more information, email info@buildbotics.com

\******************************************************************************/

/**
 * Semantic Version class following SemVer specification with custom pre-release identifiers.
 *
 * Format: MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]
 * Pre-release identifiers: dev, alpha, beta, rc
 */
class Version {
  /**
   * Valid pre-release identifiers in order of precedence (lowest to highest)
   */
  static PRERELEASE_IDENTIFIERS = ['dev', 'alpha', 'beta', 'rc'];

  /**
   * Regex pattern for SemVer validation
   */
  static SEMVER_PATTERN = /^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z][a-zA-Z0-9]*(?:\.[a-zA-Z0-9]+)*))?(?:\+([a-zA-Z0-9](?:\.[a-zA-Z0-9]+)*))?$/;

  /**
   * Initialize Version object from version string.
   *
   * @param {string} versionString - Version string in SemVer format
   * @throws {Error} If version string is invalid
   */
  constructor(versionString) {
    this.versionString = versionString;
    this.major = 0;
    this.minor = 0;
    this.patch = 0;
    this.prerelease = null;
    this.build = null;

    this._parse(versionString);
  }

  /**
   * Parse version string and validate format.
   *
   * @private
   * @param {string} versionString
   */
  _parse(versionString) {
    const match = versionString.match(Version.SEMVER_PATTERN);
    if (!match) {
      throw new Error(`Invalid version format: ${versionString}`);
    }

    this.major = parseInt(match[1], 10);
    this.minor = parseInt(match[2], 10);
    this.patch = parseInt(match[3], 10);

    if (match[4]) { // Has prerelease
      this.prerelease = match[4];
    }

    if (match[5]) { // Has build metadata
      this.build = match[5];
    }

    this._validatePrerelease();
  }

  /**
   * Validate prerelease identifier format.
   *
   * @private
   */
  _validatePrerelease() {
    if (!this.prerelease) {
      return;
    }

    const parts = this.prerelease.split('.');
    if (!Version.PRERELEASE_IDENTIFIERS.includes(parts[0])) {
      throw new Error(`Invalid prerelease identifier: ${parts[0]}`);
    }

    // Validate numeric part for known identifiers
    if (parts.length >= 2) {
      const num = parseInt(parts[1], 10);
      if (isNaN(num)) {
        throw new Error(`Prerelease identifier must have numeric part: ${this.prerelease}`);
      }
    }
  }

  /**
   * Parse version string and return Version object.
   *
   * @static
   * @param {string} versionString
   * @returns {Version}
   */
  static parse(versionString) {
    return new Version(versionString);
  }

  /**
   * Check if version string is valid SemVer format.
   *
   * @static
   * @param {string} versionString
   * @returns {boolean}
   */
  static isValid(versionString) {
    try {
      new Version(versionString);
      return true;
    } catch (e) {
      return false;
    }
  }

  /**
   * Return version string.
   *
   * @returns {string}
   */
  toString() {
    return this.versionString;
  }

  /**
   * Check equality with another Version.
   *
   * @param {Version|object} other
   * @returns {boolean}
   */
  equals(other) {
    if (!(other instanceof Version)) {
      return false;
    }
    return this.versionString === other.versionString;
  }

  /**
   * Compare this version with another version.
   *
   * @private
   * @param {Version} other
   * @returns {number} -1 if this < other, 0 if equal, 1 if this > other
   */
  _compare(other) {
    // Compare major.minor.patch
    const parts = [
      [this.major, other.major],
      [this.minor, other.minor],
      [this.patch, other.patch]
    ];

    for (const [selfPart, otherPart] of parts) {
      if (selfPart !== otherPart) {
        return selfPart > otherPart ? 1 : -1;
      }
    }

    // Compare prerelease
    if (this.prerelease && !other.prerelease) {
      return -1; // Prerelease < final release
    } else if (!this.prerelease && other.prerelease) {
      return 1;   // Final release > prerelease
    } else if (this.prerelease && other.prerelease) {
      return this._comparePrerelease(other.prerelease);
    }

    return 0; // Equal
  }

  /**
   * Compare prerelease identifiers.
   *
   * @private
   * @param {string} otherPrerelease
   * @returns {number}
   */
  _comparePrerelease(otherPrerelease) {
    const selfParts = this.prerelease.split('.');
    const otherParts = otherPrerelease.split('.');

    // Compare identifier precedence
    const selfIdx = Version.PRERELEASE_IDENTIFIERS.indexOf(selfParts[0]);
    const otherIdx = Version.PRERELEASE_IDENTIFIERS.indexOf(otherParts[0]);

    if (selfIdx !== otherIdx) {
      return selfIdx > otherIdx ? 1 : -1;
    }

    // Same identifier type, compare numeric parts
    if (selfParts.length >= 2 && otherParts.length >= 2) {
      const selfNum = parseInt(selfParts[1], 10);
      const otherNum = parseInt(otherParts[1], 10);
      if (selfNum !== otherNum) {
        return selfNum > otherNum ? 1 : -1;
      }
    }

    return 0;
  }

  /**
   * Check if this version is less than another version.
   *
   * @param {Version} other
   * @returns {boolean}
   */
  lt(other) {
    return this._compare(other) < 0;
  }

  /**
   * Check if this version is less than or equal to another version.
   *
   * @param {Version} other
   * @returns {boolean}
   */
  lte(other) {
    return this._compare(other) <= 0;
  }

  /**
   * Check if this version is greater than another version.
   *
   * @param {Version} other
   * @returns {boolean}
   */
  gt(other) {
    return this._compare(other) > 0;
  }

  /**
   * Check if this version is greater than or equal to another version.
   *
   * @param {Version} other
   * @returns {boolean}
   */
  gte(other) {
    return this._compare(other) >= 0;
  }

  /**
   * Check if this is a prerelease version.
   *
   * @returns {boolean}
   */
  isPrerelease() {
    return this.prerelease !== null;
  }

  /**
   * Check if this is a development release.
   *
   * @returns {boolean}
   */
  isDevelopment() {
    return this.prerelease && this.prerelease.startsWith('dev');
  }

  /**
   * Check if this is an alpha release.
   *
   * @returns {boolean}
   */
  isAlpha() {
    return this.prerelease && this.prerelease.startsWith('alpha');
  }

  /**
   * Check if this is a beta release.
   *
   * @returns {boolean}
   */
  isBeta() {
    return this.prerelease && this.prerelease.startsWith('beta');
  }

  /**
   * Check if this is a release candidate.
   *
   * @returns {boolean}
   */
  isReleaseCandidate() {
    return this.prerelease && this.prerelease.startsWith('rc');
  }

  /**
   * Get the development stage of this version.
   *
   * @returns {string}
   */
  getStage() {
    if (!this.isPrerelease()) {
      return 'final';
    } else if (this.isDevelopment()) {
      return 'development';
    } else if (this.isAlpha()) {
      return 'alpha';
    } else if (this.isBeta()) {
      return 'beta';
    } else if (this.isReleaseCandidate()) {
      return 'release-candidate';
    } else {
      return 'unknown';
    }
  }

  /**
   * Return new version with major bumped.
   *
   * @returns {Version}
   */
  bumpMajor() {
    return new Version(`${this.major + 1}.0.0`);
  }

  /**
   * Return new version with minor bumped.
   *
   * @returns {Version}
   */
  bumpMinor() {
    return new Version(`${this.major}.${this.minor + 1}.0`);
  }

  /**
   * Return new version with patch bumped.
   *
   * @returns {Version}
   */
  bumpPatch() {
    return new Version(`${this.major}.${this.minor}.${this.patch + 1}`);
  }

  /**
   * Return new version with prerelease bumped.
   *
   * @returns {Version}
   * @throws {Error} If not a prerelease version
   */
  bumpPrerelease() {
    if (!this.prerelease) {
      throw new Error('Cannot bump prerelease on final version');
    }

    const parts = this.prerelease.split('.');
    if (parts.length >= 2) {
      const num = parseInt(parts[1], 10) + 1;
      return new Version(`${this.major}.${this.minor}.${this.patch}-${parts[0]}.${num}`);
    } else {
      return new Version(`${this.major}.${this.minor}.${this.patch}-${parts[0]}.1`);
    }
  }

  /**
   * Return final version (without prerelease).
   *
   * @returns {Version}
   */
  toFinal() {
    return new Version(`${this.major}.${this.minor}.${this.patch}`);
  }

  /**
   * Move to next development stage.
   *
   * @returns {Version}
   */
  nextStage() {
    if (this.isDevelopment()) {
      return new Version(`${this.major}.${this.minor}.${this.patch}-alpha.1`);
    } else if (this.isAlpha()) {
      return new Version(`${this.major}.${this.minor}.${this.patch}-beta.1`);
    } else if (this.isBeta()) {
      return new Version(`${this.major}.${this.minor}.${this.patch}-rc.1`);
    } else if (this.isReleaseCandidate()) {
      return new Version(`${this.major}.${this.minor}.${this.patch}`);
    } else {
      // Final version - bump minor for next development cycle
      return new Version(`${this.major}.${this.minor + 1}.0-dev.1`);
    }
  }

  /**
   * Return version with build metadata.
   *
   * @param {string} build
   * @returns {Version}
   */
  withBuild(build) {
    let base = `${this.major}.${this.minor}.${this.patch}`;
    if (this.prerelease) {
      base += `-${this.prerelease}`;
    }
    return new Version(`${base}+${build}`);
  }
}

/**
 * Parse version string and return Version object.
 *
 * @param {string} versionString
 * @returns {Version}
 */
function parseVersion(versionString) {
  return Version.parse(versionString);
}

/**
 * Compare two version strings.
 *
 * @param {string} version1
 * @param {string} version2
 * @returns {number} -1 if version1 < version2, 0 if equal, 1 if version1 > version2
 */
function compareVersions(version1, version2) {
  const v1 = new Version(version1);
  const v2 = new Version(version2);
  return v1._compare(v2);
}

/**
 * Check if version1 is less than version2.
 *
 * @param {string} version1
 * @param {string} version2
 * @returns {boolean}
 */
function versionLess(version1, version2) {
  return compareVersions(version1, version2) < 0;
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { Version, parseVersion, compareVersions, versionLess };
} else if (typeof window !== 'undefined') {
  window.Version = Version;
  window.parseVersion = parseVersion;
  window.compareVersions = compareVersions;
  window.versionLess = versionLess;
}