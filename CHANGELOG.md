# Changelog

## v2.0.1

### Fixed
- Retry login automatically after `401` authentication expiry.
- Retry one time for transient network request failures such as connection reset.
- Keep cached device data when a house device list refresh fails.
- Prevent entity state updates from crashing with `IndexError: list index out of range`.
- Fix scheduled login callback compatibility with Home Assistant timer callbacks.
- Clean up integration listeners on unload without closing Home Assistant shared sessions.

### User-visible improvements
- Reduced cases where device state stops updating in Home Assistant.
- Reduced cases where device control fails after token expiry.
- Improved troubleshooting guidance for login timeout, device list refresh failure, and network errors.
