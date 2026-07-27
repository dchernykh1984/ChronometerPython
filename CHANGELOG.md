# Changelog

## [0.1.5](https://github.com/dchernykh1984/ChronometerPython/compare/v0.1.4...v0.1.5) (2026-07-27)


### Bug Fixes

* give the macos bundle a proper identifier and version ([a178869](https://github.com/dchernykh1984/ChronometerPython/commit/a17886966b6839195dac28f1c7ce4b6d428ca41a))

## [0.1.4](https://github.com/dchernykh1984/ChronometerPython/compare/v0.1.3...v0.1.4) (2026-07-25)


### Bug Fixes

* keep uv.lock in step with the released version ([7bca9e7](https://github.com/dchernykh1984/ChronometerPython/commit/7bca9e7da6f28800643a6f78361f2eca7e8a676b))

## [0.1.3](https://github.com/dchernykh1984/ChronometerPython/compare/v0.1.2...v0.1.3) (2026-07-25)


### Documentation

* explain how to run the app from a release ([9e0e757](https://github.com/dchernykh1984/ChronometerPython/commit/9e0e757f5cb8a23c28aa0df21586f0d64bd56c8b))

## [0.1.2](https://github.com/dchernykh1984/ChronometerPython/compare/v0.1.1...v0.1.2) (2026-07-22)


### Bug Fixes

* embed the app icon in the macOS build ([e3f70e1](https://github.com/dchernykh1984/ChronometerPython/commit/e3f70e1189ed420b1b0528e3474ac03dfa145d77))

## [0.1.1](https://github.com/dchernykh1984/ChronometerPython/compare/v0.1.0...v0.1.1) (2026-07-21)


### Bug Fixes

* reliable release builds (linux-aarch64 on ubuntu-24.04, drop Intel macOS) ([a99de44](https://github.com/dchernykh1984/ChronometerPython/commit/a99de445dcdfce0f9ebe22b7cdb65c84dc1e9262))

## 0.1.0 (2026-07-21)


### Features

* add Get groups button to load the group list from the site ([db12671](https://github.com/dchernykh1984/ChronometerPython/commit/db12671a256e51066c50bc1a7bc9ab40f65986af))
* **http:** auto-upload finish/group/remote timing data to the site ([765ecf2](https://github.com/dchernykh1984/ChronometerPython/commit/765ecf20363d6f1f9ec264faee10bbda89e709ae))
* persist fetched group list to groupsList.txt after Get groups ([6e5d08d](https://github.com/dchernykh1984/ChronometerPython/commit/6e5d08d7a58b7a8c5db18e7f88475e5a79da7174))
* port WindowsChronometer from C++ to PySide6 ([718b201](https://github.com/dchernykh1984/ChronometerPython/commit/718b201b526abf29c166a9c9b592f616d5eb48cb))
* record a disqualification reason as DSQ: reason ([d1910bd](https://github.com/dchernykh1984/ChronometerPython/commit/d1910bdb3b5da34ae1cc146171a5c1a6811a37ec))
* resolve app data next to the executable for portable builds ([e9da7e2](https://github.com/dchernykh1984/ChronometerPython/commit/e9da7e29ebf0eeeeb354c0b6eb0684e2a06757bf))
* set app name and icon at QApplication level for dock/taskbar ([127293a](https://github.com/dchernykh1984/ChronometerPython/commit/127293a731c88c68f26a4b1171a4cad4160826c4))


### Bug Fixes

* apply an empty group list from the site instead of keeping stale groups ([fe1462f](https://github.com/dchernykh1984/ChronometerPython/commit/fe1462f72a1581f011e94c0cbdc320f8964a462d))
* debounce save_http_config to avoid disk writes on every keystroke ([3b2ceaa](https://github.com/dchernykh1984/ChronometerPython/commit/3b2ceaa91c8352ca27a6e4c9d605552203aea0ca))
* defer file-error dialog to avoid blocking inside eventFilter key handler ([77c3bd7](https://github.com/dchernykh1984/ChronometerPython/commit/77c3bd775f34e6bc83d1f7a75ca1014129aade75))
* disconnect upload workers and wait before closing to prevent crash ([0a8170d](https://github.com/dchernykh1984/ChronometerPython/commit/0a8170db2830fa375bfb14f0128dec44e295c107))
* don't clear Next field on Save all Clear ([fc3401d](https://github.com/dchernykh1984/ChronometerPython/commit/fc3401dd41aa4b3d9b78e2a6790740f4fde2ea42))
* don't shift/clear UI fields when write to results file fails ([16e0345](https://github.com/dchernykh1984/ChronometerPython/commit/16e03453761c1afbd0fb86b1d92d17df070d5df5))
* enable Freeze file paths by default and lock fields on startup ([9b68a3e](https://github.com/dchernykh1984/ChronometerPython/commit/9b68a3e8b6d47dbbfb180264ace5a75ce727ee37))
* guard UI mutations against write failures in shift, DSQ, and save-all ([84e7ae1](https://github.com/dchernykh1984/ChronometerPython/commit/84e7ae14a827c3610639456ed96cb94e5db66ce7))
* improve save error handling and rename config button ([dff059d](https://github.com/dchernykh1984/ChronometerPython/commit/dff059db96a4715f9cf42dd875bc1afd6fa91306))
* install dev deps into system Python to fix pytest not found in CI ([32fc786](https://github.com/dchernykh1984/ChronometerPython/commit/32fc786d0c25ae60d40125d76fdb4bf3c9e8065a))
* install only dev deps in CI to avoid PySide6 on headless Ubuntu ([aeb5c7e](https://github.com/dchernykh1984/ChronometerPython/commit/aeb5c7e1a3fa7d25e141dbbff4b591dafca0da27))
* make finish time slots editable and expand group selector to full width ([adc7ec8](https://github.com/dchernykh1984/ChronometerPython/commit/adc7ec8ceb7c43743fcd5340b30564c35290e419))
* make group time field editable with default value and track focused slot for second-user workflow ([6dd0f6f](https://github.com/dchernykh1984/ChronometerPython/commit/6dd0f6f953db7ecddc8220ef26f4d1efe7e76657))
* normalize config file paths (backslash→slash), use Path for temp backup ([8f27c9b](https://github.com/dchernykh1984/ChronometerPython/commit/8f27c9bbb808623c5fd01f03deefa9d5398382bd))
* read results/groups file inside upload worker thread, not on main thread ([5a33f3f](https://github.com/dchernykh1984/ChronometerPython/commit/5a33f3f9924957e4393453a94b478967df76cd0c))
* show current wall-clock time instead of elapsed time since launch ([bb9bbec](https://github.com/dchernykh1984/ChronometerPython/commit/bb9bbec2a7aa469e3060914d221fea78fc4410cf))
* wait for in-flight upload threads before accepting window close ([9068f21](https://github.com/dchernykh1984/ChronometerPython/commit/9068f21e14e17544b962be0a18716e3278907b5c))


### Documentation

* add contributing guidelines to README ([085889d](https://github.com/dchernykh1984/ChronometerPython/commit/085889d44e5eba40fa5dac984d783e7a61b6ea35))
* add Running the application section to README ([acd7874](https://github.com/dchernykh1984/ChronometerPython/commit/acd7874d25dad06d9332fcac2b9c4b73a1323938))
* add setup instructions to README ([5fdab95](https://github.com/dchernykh1984/ChronometerPython/commit/5fdab95a29fa9cf4ba84c4bcd582ef85d89449b2))
* document pre-commit setup and manual run command ([d9b5323](https://github.com/dchernykh1984/ChronometerPython/commit/d9b5323527004ff548110b4a5c1c31190ede102e))
