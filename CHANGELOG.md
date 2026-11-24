# Changelog

## [0.8.1](https://github.com/dchernykh1984/ChronometerPython/compare/v0.8.0...v0.8.1) (2026-11-24)


### Bug Fixes

* **groups:** saving a group typed in takes that group off the list, not another one ([e4038fc](https://github.com/dchernykh1984/ChronometerPython/commit/e4038fcc66bb8cc26f819792f366ce0fd27cb52a))


### Documentation

* **specs:** a beam break and the second judge's FINISH come in at the bottom slot with the Next number ([5f4e236](https://github.com/dchernykh1984/ChronometerPython/commit/5f4e236fdcfd6b7f333e56d391f9406da2d87fcb))
* **specs:** a beam break takes a slot with Beam records at Rider cutoffs, and starts the group at Group starts ([71a8a23](https://github.com/dchernykh1984/ChronometerPython/commit/71a8a23a33d220b58adf69afd58aa98e47b6e3f9))
* **specs:** a start given by hand is never replaced by a beam break, and every break with no group chosen is named ([478e822](https://github.com/dchernykh1984/ChronometerPython/commit/478e822b016c3ecb90ef8cac97f00e7620ab9fdb))
* **specs:** any edit of the group's time field by hand, emptying it too, keeps the beam from filling it ([c204898](https://github.com/dchernykh1984/ChronometerPython/commit/c204898fd3bf32e9d45b43c006812a41e87f9905))
* **specs:** Beam records is locked while a source runs, and kept in the sources file ([ac97cd1](https://github.com/dchernykh1984/ChronometerPython/commit/ac97cd12d14a3b45f20a1a8baed36794265a02c2))
* **specs:** the quickstart's beam break comes in at the bottom slot with the Next number ([cb3a15b](https://github.com/dchernykh1984/ChronometerPython/commit/cb3a15bad4b8b5658949785d04033aa456c8a8e0))
* **specs:** the source choices are free again at Stop; only the paths and Load race config wait for the connector to end ([788e863](https://github.com/dchernykh1984/ChronometerPython/commit/788e86375ced2a24afdf5342e63438ea62030c47))

## [0.8.0](https://github.com/dchernykh1984/ChronometerPython/compare/v0.7.1...v0.8.0) (2026-11-23)


### Features

* **beam:** enclosures with the electronics printed in: three PETG parts, the lens focused by its hood ([f637d48](https://github.com/dchernykh1984/ChronometerPython/commit/f637d48b7fa1db33ea807e89d9df676b3687d87d))
* **beam:** second enclosures: six PETG parts sealed with silicone, a 100 mm hood over the lens ([19345bc](https://github.com/dchernykh1984/ChronometerPython/commit/19345bc1bd06cce78a2fadab026c4db7aa7e15ea))


### Bug Fixes

* **beam:** a 0.6 mm chamfer on the tube's front and the carriage's bed edge, where the first layers flare ([490239a](https://github.com/dchernykh1984/ChronometerPython/commit/490239a75ccc4e67e055085620c77a8b79443d59))
* **beam:** the enclosure script stops when it cannot find its folder, never emptying a stl/ elsewhere ([cf42704](https://github.com/dchernykh1984/ChronometerPython/commit/cf42704182e0518665b3bbc5e264b48f7ede556b))
* **beam:** the printed-in body's trimmer hole 8 mm across, for a trimmer off the module's middle ([b2b21d0](https://github.com/dchernykh1984/ChronometerPython/commit/b2b21d04a398d539310b0b73ef02de089a035e24))
* **beam:** the printed-in emitter 10 mm longer, so its power module and the cable's plug fit behind the laser ([ad65f80](https://github.com/dchernykh1984/ChronometerPython/commit/ad65f8058724665017caa93caf0b3032d1627271))


### Documentation

* **beam:** a bag of silica gel in each sealed part, or a cold night mists the lens from inside ([1e6e800](https://github.com/dchernykh1984/ChronometerPython/commit/1e6e80017c80a3d0aec8b5e12a2d0892cbc2561f))
* **beam:** a brim for the tube and the hood, tall parts on narrow rings ([7a7707e](https://github.com/dchernykh1984/ChronometerPython/commit/7a7707e4894d40cf2e2dc3fbd1a9d19d254003a1))
* **beam:** a photoresistor on leads too short to bend forward soldered on two short wires ([3165fbb](https://github.com/dchernykh1984/ChronometerPython/commit/3165fbb6405aa86e6b00413960086267f8d81343))
* **beam:** a printed-in board re-flashed over its cable, MicroPython too, with no button to reach ([713f938](https://github.com/dchernykh1984/ChronometerPython/commit/713f9386eff8761e388941270299c5b3fab19624))
* **beam:** a printed-in part's cable taped to the bed, so the printer's moves cannot catch it ([518cce8](https://github.com/dchernykh1984/ChronometerPython/commit/518cce858b3a84245cc2ab12aa7314742a34edc8))
* **beam:** bare pins taped over before they are printed in, where a short cannot be reached ([bf9e869](https://github.com/dchernykh1984/ChronometerPython/commit/bf9e869305227246e3392f2cbaa05c001ec4ea29))
* **beam:** each USB cable tied to its tripod, so a pull never reaches a board's socket ([b29f117](https://github.com/dchernykh1984/ChronometerPython/commit/b29f1171e3e3e76bbbed37bacb5d71d90d9a69fe))
* **beam:** hot glue over the receiver's tripod nut, its slot open along the tube ([80a2514](https://github.com/dchernykh1984/ChronometerPython/commit/80a2514b3ed78862c06deebd4b4c0b0b8dc10979))
* **beam:** the beam's and the assembled enclosures' READMEs point to the printed-in version ([a24d23d](https://github.com/dchernykh1984/ChronometerPython/commit/a24d23dfa3b7a3a199c15ac04a1edb0f76e1d393))
* **beam:** the beam's steps say the printed-in sensor's trimmer is set after the print, through its hole ([f859dd3](https://github.com/dchernykh1984/ChronometerPython/commit/f859dd3f29da4655ce85c3ff0e5269fc5a4c5fde))
* **beam:** the carriage fixed with silicone a nozzle reaches, the laser's barrel at its hole, not in it ([f77e1e7](https://github.com/dchernykh1984/ChronometerPython/commit/f77e1e737bc47ce5a2c8d2c5e397fd63cc1c91c1))
* **beam:** the carriage's slot taped round the module, so no light from behind reaches the sensor ([12c2eb4](https://github.com/dchernykh1984/ChronometerPython/commit/12c2eb44830ed330fe925b7f458bd95bc9a42159))
* **beam:** the emitter printed light, so its laser keeps cool in the sun ([fe3a7be](https://github.com/dchernykh1984/ChronometerPython/commit/fe3a7be5c998bad8415159077d5aa05bf7f8d744))
* **beam:** the emitter's parts row says the laser shines through its hole, as the assembly has it ([d7f3a2c](https://github.com/dchernykh1984/ChronometerPython/commit/d7f3a2c5dede89902297ab3d67eb96598af57efe))
* **beam:** the laser's load resistor stood clear of the box, its half watt hotter than PETG takes ([75f1f00](https://github.com/dchernykh1984/ChronometerPython/commit/75f1f00039c289da3729cd2ed7bfb082d3d645b3))
* **beam:** the laser's power module every kit buys, a copy of Adafruit's 4090, so both enclosures fit it as they are ([7f78bb7](https://github.com/dchernykh1984/ChronometerPython/commit/7f78bb733f9f25142addefcdeed93b7ec3e3df54))
* **beam:** the laser's silicone kept off its front glass, or the spot smears at 10 m ([dce8294](https://github.com/dchernykh1984/ChronometerPython/commit/dce829492a0b3530870f31f252d79846927f8c5b))
* **beam:** the printed-in board stood on an edge, its LED at the window 10 mm over the bay's floor ([bb7ffc4](https://github.com/dchernykh1984/ChronometerPython/commit/bb7ffc451cdb8f036484f85b37172b60bd732b49))
* **beam:** the printed-in board's buttons kept clear of its tape and the wall, or it never starts ([5991a72](https://github.com/dchernykh1984/ChronometerPython/commit/5991a723c31c606b7250f67ff126b83fe95bc032))
* **beam:** the printed-in extension cable one that carries data, as the board is read and flashed through it ([cf27d5e](https://github.com/dchernykh1984/ChronometerPython/commit/cf27d5e74161e033c2f98dbc3c371ab049043f8f))
* **beam:** the printed-in hood taped where it focuses while its silicone cures ([59d9c02](https://github.com/dchernykh1984/ChronometerPython/commit/59d9c026a4f59000a94c2bf01138255b63cd0545))
* **beam:** the printed-in module's trimmer turned towards its hole, a quarter turn from the boss ([5874a81](https://github.com/dchernykh1984/ChronometerPython/commit/5874a81941428b8e60423945a475fd469c655f46))
* **beam:** the printed-in parts list has the tape that holds the hood while its silicone cures ([013cd6c](https://github.com/dchernykh1984/ChronometerPython/commit/013cd6c89356b16d78dac96f69105ec9ce87155d))
* **beam:** the printed-in pause tried on a small print first, and everything ready before it ([6b75045](https://github.com/dchernykh1984/ChronometerPython/commit/6b7504521767c4bd9b852bf1ed2597ab5865ab55))
* **beam:** the printed-in README's opening and measuring lines wrapped again ([070071d](https://github.com/dchernykh1984/ChronometerPython/commit/070071ded1393628b575309e722cc9a18f9cda25))
* **beam:** the printed-in receiver on its tripod before its trimmer is set with the laser aimed at it ([83f4a58](https://github.com/dchernykh1984/ChronometerPython/commit/83f4a58dd0e05de8d58d8fd2a5c67c94489bb0bb))
* **beam:** the printed-in script says the hood is pulled off the body for a longer focus, not back ([1370094](https://github.com/dchernykh1984/ChronometerPython/commit/137009429d88fec153ce3bdde84b5dff0fbf4709))
* **beam:** the printed-in trimmer 30 mm in, so a screwdriver's shaft longer than that ([e9a1a5f](https://github.com/dchernykh1984/ChronometerPython/commit/e9a1a5f871e5cb855ce0d734b38d1c4fd7d38d11))
* **beam:** the sensor step's lines wrapped again ([4893ee8](https://github.com/dchernykh1984/ChronometerPython/commit/4893ee82496ea6deb0702699257c5276125431d7))
* **beam:** the tube and the hood in one piece would be about 270 mm, not 280 ([a46f5ac](https://github.com/dchernykh1984/ChronometerPython/commit/a46f5acfd4cede254a5a1f1d89505a51a04bd871))
* CLAUDE.md and AGENTS.md name both enclosure folders and their scripts ([a3a8ee1](https://github.com/dchernykh1984/ChronometerPython/commit/a3a8ee19937eb6885a9e88b46ef2bd5960632552))
* **specs:** spec 002 keeps the printed-in enclosures beside the second ones until a print chooses ([7e9edbf](https://github.com/dchernykh1984/ChronometerPython/commit/7e9edbffc8c1632b59a34c88595cbbd9a427554f))
* **specs:** spec 002 says which parts take a tripod's nut, not each side ([b948062](https://github.com/dchernykh1984/ChronometerPython/commit/b9480627aa30a0d3d59a7654d47a96928083ac3b))
* **specs:** spec 002's checklist says how the second enclosures are sealed ([a53b5a9](https://github.com/dchernykh1984/ChronometerPython/commit/a53b5a9359feee4a74efd8b9ad42a844d49cb723))
* **specs:** spec 002's second enclosures: six parts, silicone, a 100 mm hood, a red film ([b7693fc](https://github.com/dchernykh1984/ChronometerPython/commit/b7693fc47f412502733bbaa0d145140627293b6d))

## [0.7.1](https://github.com/dchernykh1984/ChronometerPython/compare/v0.7.0...v0.7.1) (2026-11-22)


### Bug Fixes

* **beam:** FLASH puts a lit one-colour LED out, so Blink shows with the laser aimed (firmware 0.5) ([cbf523e](https://github.com/dchernykh1984/ChronometerPython/commit/cbf523e5028f69f2f0ddf43a0a4b620cf86b50b3))


### Documentation

* **beam:** firmware 0.5 and Blink seen on an ESP32-C3 with its laser aimed ([e061798](https://github.com/dchernykh1984/ChronometerPython/commit/e0617988a68a0123bf8585a30bf8281b62722ca0))
* **specs:** spec 003's context and plan with firmware 0.5's one change ([ac0c3b9](https://github.com/dchernykh1984/ChronometerPython/commit/ac0c3b9e616652dac27e4d91ec551075cfd61ec6))

## [0.7.0](https://github.com/dchernykh1984/ChronometerPython/compare/v0.6.0...v0.7.0) (2026-11-22)


### Features

* **beam:** find the boards around on USB and Bluetooth ([5df96b1](https://github.com/dchernykh1984/ChronometerPython/commit/5df96b1b7ca70f3e31e5346cc576f9f708d31d94))
* **beam:** pick the boards from a list in the window, with Blink ([8cd3a6d](https://github.com/dchernykh1984/ChronometerPython/commit/8cd3a6d58a812a0c1748f58463d6a5e2576bab96))
* **beam:** read every board picked at once, each break a cutoff of its own ([bfd2254](https://github.com/dchernykh1984/ChronometerPython/commit/bfd2254a4bdb7135445385bb991a5dd429d1e29d))
* **clock:** every stamp on the device's clock, and the judge shown where it comes from ([1c8fe7d](https://github.com/dchernykh1984/ChronometerPython/commit/1c8fe7d902c747cdb5bfa80eb5fcb84f0f4f1189))
* **clock:** measure the device's clock against world time by NTP ([bf33ec7](https://github.com/dchernykh1984/ChronometerPython/commit/bf33ec7c3cb7cd4d57999bebf25a2feb4d35e97c))


### Bug Fixes

* **beam:** a board picked by its name before is the board found of that name, listed once ([fcca460](https://github.com/dchernykh1984/ChronometerPython/commit/fcca460298b05c153650aedb1c5b0c1685e550fa))
* **beam:** a board picked on USB is found by its serial number in any socket ([c1ebc7a](https://github.com/dchernykh1984/ChronometerPython/commit/c1ebc7acd7846a73548c4ddd75f53f0d9d7c34c4))
* **beam:** a board picked with no address or port is said, not left out unseen ([01d6dd3](https://github.com/dchernykh1984/ChronometerPython/commit/01d6dd30f7194b26efc93009882a2e3843f23ea6))
* **beam:** a board the source reads is said read in the list, not lost ([6148a85](https://github.com/dchernykh1984/ChronometerPython/commit/6148a85349bd276c430195d0ba232178237da03a))
* **beam:** a flash due for a board let go since is not written ([2b5e91a](https://github.com/dchernykh1984/ChronometerPython/commit/2b5e91a82eb5fb9c79db3d7a57f2a269ca586d85))
* **beam:** a name a device around advertises keeps no control character, nor cuts a log line ([6b8192b](https://github.com/dchernykh1984/ChronometerPython/commit/6b8192b035b34743870dc9a37ba1be6682e13f79))
* **beam:** a search or a blink that hangs is stopped after a minute, and said ([3236c78](https://github.com/dchernykh1984/ChronometerPython/commit/3236c782d65a0f2b7fde690ef5ad4db07019fa8a))
* **beam:** at stop every board's waiting breaks go out before any link is let go ([4f1b0b6](https://github.com/dchernykh1984/ChronometerPython/commit/4f1b0b694c62a7d91f35c42ed09e3f3cdbfff8b7))
* **beam:** the board chosen in the list stays chosen as the source starts and stops ([0554275](https://github.com/dchernykh1984/ChronometerPython/commit/05542759c4d1337a1c7a739aa248f240156a472e))
* **clock:** an NTP server's addresses are tried in turn, an IPv6 one going nowhere passed by ([7938374](https://github.com/dchernykh1984/ChronometerPython/commit/79383749a71da32970e7b3fce942064e3d69a93e))
* **clock:** the device clock runs on a clock that goes on while the computer sleeps ([a1a4d1b](https://github.com/dchernykh1984/ChronometerPython/commit/a1a4d1b313da1253a15f704624f9e459f729bfcf))


### Documentation

* **beam:** a board on USB found by its serial number in any socket ([af9685a](https://github.com/dchernykh1984/ChronometerPython/commit/af9685a0e4f5a64257e263f03541c8ef436b893f))
* **beam:** how long a search for the boards really takes ([9addea6](https://github.com/dchernykh1984/ChronometerPython/commit/9addea6fe6275cab13b1803a46cf58a40baf3cea))
* **beam:** the Android app's boards picked from a list ([459ffdf](https://github.com/dchernykh1984/ChronometerPython/commit/459ffdfe2764a4904e04956ff1c74a66d4b8aec1))
* **beam:** the log's lines of a search or a blink stopped, and a board read now ([0096e2f](https://github.com/dchernykh1984/ChronometerPython/commit/0096e2f991eb226210fd76f39a7d46fd25d4243f))
* **specs:** GNSS's checks and the best source as the phone builds them, its tasks done ([359515c](https://github.com/dchernykh1984/ChronometerPython/commit/359515c4454bba0950359155112ebdfc6d79f42f))
* **specs:** the boards around listed within 15 s, as a portable build unpacks first ([054a275](https://github.com/dchernykh1984/ChronometerPython/commit/054a275bbc242ddac913423f2e48670684aa7c42))
* **specs:** the boards around picked from a list, and a clock that knows world time ([d43b062](https://github.com/dchernykh1984/ChronometerPython/commit/d43b062b744d16c5f1c01d197f7008387994aa19))
* **specs:** the chronometer as it works today, with its boards around and device clock ([4d5700c](https://github.com/dchernykh1984/ChronometerPython/commit/4d5700c359606be25b75f369037de6c4965c1f84))
* **specs:** the device clock on a monotonic clock that goes on while it sleeps ([e9e92e4](https://github.com/dchernykh1984/ChronometerPython/commit/e9e92e4edf5e665ea8c2fc1dd2fb8ff2f59c56a7))
* **specs:** the plan and FR-012 as built, the desktop tasks done ([3f2d2d3](https://github.com/dchernykh1984/ChronometerPython/commit/3f2d2d368e4adc76a96ea757426f997c625c2e26))
* the boards picked from a list, Blink and the device clock ([6eeab6f](https://github.com/dchernykh1984/ChronometerPython/commit/6eeab6f7b8fd36a3d075e0b1fa861bd3506ec86c))

## [0.6.0](https://github.com/dchernykh1984/ChronometerPython/compare/v0.5.0...v0.6.0) (2026-11-22)


### Features

* **beam:** a clock check for every board flashed, over its cable and its radio at once ([e3c621a](https://github.com/dchernykh1984/ChronometerPython/commit/e3c621a9b1b79214f994977225cfc9ea9c63e89d))
* **beam:** first enclosures from Blender: a lens tube receiver, a laser box, TPU gaskets, a tripod collar ([b73a4ca](https://github.com/dchernykh1984/ChronometerPython/commit/b73a4ca1358dd781c6079b39c5e13b3c9975d384))
* **beam:** one firmware core for the RP2040 with its BT05 and for the ESP32-C3's Bluetooth ([91a6cd8](https://github.com/dchernykh1984/ChronometerPython/commit/91a6cd864d8db22903ecbec04f8b7b14414ca344))
* **beam:** PING a Bluetooth board every 0.5 s, its clock from the last 32 answers ([870a335](https://github.com/dchernykh1984/ChronometerPython/commit/870a3351ab77396565672262b3b8a5d5f87996e6))
* **beam:** read contract 0.4: both moments of a PONG, the radio's clock, breaks asked for again ([d499b11](https://github.com/dchernykh1984/ChronometerPython/commit/d499b11fe255e845d94ca5f8f47ae9c0c63d257e))
* **beam:** read the RP2040's BT05 and the ESP32-C3 over Bluetooth on the desktop ([b8c13e6](https://github.com/dchernykh1984/ChronometerPython/commit/b8c13e67d0d60e07687812870777735104698823))


### Bug Fixes

* **beam:** a board started again under a link that stayed up has its clock read anew ([addaafc](https://github.com/dchernykh1984/ChronometerPython/commit/addaafc357d94f8e92a71d0006e442bfa51e791d))
* **beam:** a collar in two halves that goes round the tube between its flanges, and room for the sensor's trimmer ([26f4453](https://github.com/dchernykh1984/ChronometerPython/commit/26f4453945996eb553a77de24700959a4464c68a))
* **beam:** a flash that will not keep the BT05's baud never stops the RP2040's start ([21e5d0e](https://github.com/dchernykh1984/ChronometerPython/commit/21e5d0e5b66fcbe282dc6388c85e3c783c036ff8))
* **beam:** a USB mapping within 3 ms, the most half its round trip allows ([5cfffc8](https://github.com/dchernykh1984/ChronometerPython/commit/5cfffc8c17b9c22b7526cf08970dd7c378faf3cb))
* **beam:** ask the board's count every 5 s, so a last break whose line was lost comes all the same ([283ab6f](https://github.com/dchernykh1984/ChronometerPython/commit/283ab6f073b4b85ebc5ca262b98c10118ad5d0e7))
* **beam:** check a board's crystal within 60 ppm, as the prototype's were measured ([69c6c50](https://github.com/dchernykh1984/ChronometerPython/commit/69c6c503d080e07f22159940f551361c084b8e64))
* **beam:** cut a USB board's line at 128 characters, as over Bluetooth ([65d753b](https://github.com/dchernykh1984/ChronometerPython/commit/65d753bd273fdb25668c3ea5c44a51ddfc61476d))
* **beam:** let go of a Bluetooth device whose serial characteristic cannot be read ([9b033ad](https://github.com/dchernykh1984/ChronometerPython/commit/9b033ad2bcc646e1e829a76d4a2b71f8a442d1cc))
* **beam:** let go of a link opened only half: a port whose lines fail, a device with no serial service ([d63d9fa](https://github.com/dchernykh1984/ChronometerPython/commit/d63d9fa3440fb9279a5d01c4ea179a70a1c82bef))
* **beam:** move the BT05 to 115200 by its own baud table, before its name ([f357802](https://github.com/dchernykh1984/ChronometerPython/commit/f357802ce34e8269695ef9e28bbd0beae6612d89))
* **beam:** open an ESP32-C3's USB port with DTR and then RTS off, never its bootloader ([5adde03](https://github.com/dchernykh1984/ChronometerPython/commit/5adde03d8488f22c589d193d9922bcc37ed8a0ac))
* **beam:** print files centred where each part was made, never moved by its neighbours ([3cabf92](https://github.com/dchernykh1984/ChronometerPython/commit/3cabf92616e372c34838e4ce9cc93da5dd8571c2))
* **beam:** say breaks again a line a turn once the link is free, so a long RESEND never holds up the next break ([94398c0](https://github.com/dchernykh1984/ChronometerPython/commit/94398c0e1d51c8b24cf0c5df32bff3727a7a805b))
* **beam:** start on an ESP32 too, whose pin interrupts are never hard ([375291d](https://github.com/dchernykh1984/ChronometerPython/commit/375291dfd2f928b0cc7e431e9760d607298b3747))
* **beam:** time a PONG over the BT05 as its first notification leaves the module ([0857170](https://github.com/dchernykh1984/ChronometerPython/commit/08571701a0961fe450b0b60ddd2c1e254b263ad6))
* **beam:** time a USB board's line by its first byte ([6de74e5](https://github.com/dchernykh1984/ChronometerPython/commit/6de74e5f6ae910a935bbb94f4ac6b3389b4b7eab))
* **beam:** write to a Bluetooth board with response where it takes no other, as the BT05 ([544dd14](https://github.com/dchernykh1984/ChronometerPython/commit/544dd1462d75c0608dbe03122800e23a3dabab16))


### Documentation

* **agents:** the beam folder, its contract-first rule, MicroPython syntax, Bluetooth and Blender ([2491ed2](https://github.com/dchernykh1984/ChronometerPython/commit/2491ed226611973027c83a3d24b8a0ae5c273df5))
* **agents:** the beam's clock check, and its clock read at every answer ([df37ca1](https://github.com/dchernykh1984/ChronometerPython/commit/df37ca1f78114881499e6c6b51f4940dc09b5b5e))
* **agents:** the prototype's hardware quirks the beam's code keeps to ([814a999](https://github.com/dchernykh1984/ChronometerPython/commit/814a9995bc4fa04b502bf2b73b86d6dba30b68cc))
* **app:** the beam boards the chronometer reads, over USB and Bluetooth ([15598b9](https://github.com/dchernykh1984/ChronometerPython/commit/15598b99caa679b991f544c95b178caa0706b5ca))
* **beam:** a beam's cost with its board, now that the receiver counts it ([8697fa7](https://github.com/dchernykh1984/ChronometerPython/commit/8697fa706e0c713fb551a660eaecfebc526939ca))
* **beam:** a break's interrupt is hard on the RP2040, scheduled on the ESP32 ([b811e4b](https://github.com/dchernykh1984/ChronometerPython/commit/b811e4b96b757afe5745b7e6ef1041dbff4bbd89))
* **beam:** a kit by default, a Bluetooth receiver and a laser on a USB-C power module ([f599311](https://github.com/dchernykh1984/ChronometerPython/commit/f599311a937218efb47c9e68d0c9da3289456025))
* **beam:** a PONG over the BT05 counts its first 20 characters' time ([8b54982](https://github.com/dchernykh1984/ChronometerPython/commit/8b5498245740b3975ddd8005c2ad9bf6f7b469e1))
* **beam:** a power bank's low-current mode lasts 2 hours: check it for a race day ([9451e4f](https://github.com/dchernykh1984/ChronometerPython/commit/9451e4f2edfc62acccd1f31b2d466798fb79ea03))
* **beam:** check the clock of every board flashed, and what its accuracy rests on ([27a42b7](https://github.com/dchernykh1984/ChronometerPython/commit/27a42b7d60b387d03879995e84538a94d1e4acc5))
* **beam:** the BT05 is moved to 115200 by its own table first, then named ([dafc3ab](https://github.com/dchernykh1984/ChronometerPython/commit/dafc3ab7a1ab6353d0dcfe05118247b2d0ed4118))
* **beam:** the prototype's clock and interrupt figures, warm ([9788b1c](https://github.com/dchernykh1984/ChronometerPython/commit/9788b1c7d3b679cfc7f9765402befc218c0e6d9c))
* **beam:** the prototype's crystals as about +46 and -41 ppm, as they vary run to run ([2463a1d](https://github.com/dchernykh1984/ChronometerPython/commit/2463a1d19c4fc5620e65f32636cfedd39b0cbf48))
* **beam:** the prototype's figures at Bluetooth's new pace, and what a time holds to ([e8af58f](https://github.com/dchernykh1984/ChronometerPython/commit/e8af58f2d4afaf9cfa5cb780a3e29134977edce1))
* **beam:** the RESEND pace, the count asked every 5 s, and Android 7 in the plan ([149fe25](https://github.com/dchernykh1984/ChronometerPython/commit/149fe25a981a628ab0aed0c79297dd268831fec4))
* **beam:** the two Bluetooth kits: what to buy and for how much, wiring, flashing, both apps ([2ae8e3a](https://github.com/dchernykh1984/ChronometerPython/commit/2ae8e3af6b665c5a7127ceccdd3b1e937a550bd9))
* **contract:** beam board lines 0.4: Bluetooth, both moments in a PONG, RESEND ([832f6af](https://github.com/dchernykh1984/ChronometerPython/commit/832f6af1c3604dc858251cb45fac5457fdf10387))
* **specs:** a board's commands go with response where its characteristic takes no other ([d234b88](https://github.com/dchernykh1984/ChronometerPython/commit/d234b882a48e098fc201e94ebc8887cd8f46d9e0))
* **specs:** a board's line is timed by its first piece over USB too ([16afec2](https://github.com/dchernykh1984/ChronometerPython/commit/16afec2d19744cfe725426f90a97fba22ab37c1e))
* **specs:** a break waits 10 s at most for the radio's clock, and how long a link was down is still to say ([499d2e4](https://github.com/dchernykh1984/ChronometerPython/commit/499d2e4fd23117f31be46ce7df7f9b4d4f09d056))
* **specs:** a kit by default, each side on a USB-C power bank ([db1882e](https://github.com/dchernykh1984/ChronometerPython/commit/db1882e2577b90d2522dd542c820fa08f078c3aa))
* **specs:** a power bank that runs out is a link lost, with no warning before ([f8b515a](https://github.com/dchernykh1984/ChronometerPython/commit/f8b515a25f40539d530baae76e5c3c135630874b))
* **specs:** a time holds to a hundredth of a second, start and finish together ([ef5ee90](https://github.com/dchernykh1984/ChronometerPython/commit/ef5ee9072a8bc7a20349e8ecdda1223b42433aa6))
* **specs:** ask for a beam ready for real races: its own time, Bluetooth, wind, weather, printed parts ([c3d4f4a](https://github.com/dchernykh1984/ChronometerPython/commit/c3d4f4afbcc676f9ace52e000240bb9cf3f9ff51))
* **specs:** ask what FR-008's power level is once the power is a power bank ([8f594aa](https://github.com/dchernykh1984/ChronometerPython/commit/8f594aa75229b6d1b21b5566e613cf619d70d48b))
* **specs:** Bluetooth's mapping moves about 0.5 ms from one answer to the next ([7ed437f](https://github.com/dchernykh1984/ChronometerPython/commit/7ed437f614492c813d87bce88cf5765f5a075053))
* **specs:** name the firmware core beamcore.py, as it is on the boards ([2831946](https://github.com/dchernykh1984/ChronometerPython/commit/283194678eaefd987f650f8105871bb358cb91e0))
* **specs:** no power level for a board on a power bank, which lasts the race ([49e6773](https://github.com/dchernykh1984/ChronometerPython/commit/49e6773cec6f04d90a888b52796970a03bb90dc8))
* **specs:** PING a Bluetooth board every 0.5 s and map its clock from the last 32 answers ([b614f90](https://github.com/dchernykh1984/ChronometerPython/commit/b614f904ebbb9f870ab2fe5ae493fce752ab8d94))
* **specs:** plan the two Bluetooth kits, contract 0.4 and the first enclosures ([3819845](https://github.com/dchernykh1984/ChronometerPython/commit/381984507485ec3f6ec5a7bc2a1404a175f0631c))
* **specs:** read the board's clock at every answer, and check it on every board flashed ([9db96d5](https://github.com/dchernykh1984/ChronometerPython/commit/9db96d5b04c22e34e5bcbecacefffd9ec8349f31))
* **specs:** require sealing, one beam folder, PETG with TPU, and a knowledge-base article ([23734d7](https://github.com/dchernykh1984/ChronometerPython/commit/23734d7ac479a80e11a94511582e400e210d332a))
* **specs:** rewrap two lines the latest changes left past the spec's width ([a582bd5](https://github.com/dchernykh1984/ChronometerPython/commit/a582bd5e5d317223b62b66d0daa3581c4f5a35cb))
* **specs:** ride out the wind with a lens and cap a beam's optics at 10,000 tenge ([1d647d1](https://github.com/dchernykh1984/ChronometerPython/commit/1d647d1a8dba3b7ce179cfcfb162b68b5c1c53e7))
* **specs:** take both Bluetooth boards, the ESP32-C3 and an HM-10 on the RP2040, and a falling-weight test ([af7b6bb](https://github.com/dchernykh1984/ChronometerPython/commit/af7b6bb23972ce6e58a9a76022c823afe5b073c6))
* **specs:** the plan gives both kits' Bluetooth figures, 1.7 to 1.8 ms ([74f19ad](https://github.com/dchernykh1984/ChronometerPython/commit/74f19ad6957f4064e29c33436ab04d06afef9933))
* **specs:** the plan times a USB line by its first piece too, as the contract does ([2d7c89e](https://github.com/dchernykh1984/ChronometerPython/commit/2d7c89e0fb30653703b0fbc3a39f02e7afd96eea))
* **specs:** the spec's checklist names FR-008's open question ([9cf4896](https://github.com/dchernykh1984/ChronometerPython/commit/9cf48964ab7c0f7a0b0972c61762a8d5cc734537))

## [0.5.0](https://github.com/dchernykh1984/ChronometerPython/compare/v0.4.1...v0.5.0) (2026-11-15)


### Features

* **beam:** bring a beam break and the second judge's stamp in at the bottom slot, as a hand cutoff ([7cc707d](https://github.com/dchernykh1984/ChronometerPython/commit/7cc707db0034a7358de9aa7a4f82470307736311))
* **beam:** choose the RP2040 beam board from the device list, the chronometer reading it itself ([bff8122](https://github.com/dchernykh1984/ChronometerPython/commit/bff81222a5130d7ac44864420cc586de3ac4176d))
* **beam:** let the beam stamp group starts, the first break after a group is chosen ([486af56](https://github.com/dchernykh1984/ChronometerPython/commit/486af562906fa8ec2af246a0d39072eeb78c6fb0))


### Bug Fixes

* **beam:** keep a group start the judge gave by hand from a beam break, until Save group ([18c12a5](https://github.com/dchernykh1984/ChronometerPython/commit/18c12a5fcff2dc5868a76365b11fb2622c90e7f8))
* **beam:** say a break was not stamped as the bottom slot had a time, not every slot ([d5dd1de](https://github.com/dchernykh1984/ChronometerPython/commit/d5dd1de6eda76c93205eb60d5e776339e486d08f))
* **beam:** say once when a break a minute after an unsaved group start is likely the next group's ([0718e9a](https://github.com/dchernykh1984/ChronometerPython/commit/0718e9a4f2c1c2370b41ecafb83de793a5373454))


### Documentation

* **specs:** tell story 4 as the beam now works, its breaks at the bottom slot and its group starts ([977180f](https://github.com/dchernykh1984/ChronometerPython/commit/977180ff357d5aa5b6289567cb0d27192827943f))
* **specs:** the beam's breaks at the bottom slot, its group starts and the board in the device list ([a04c32b](https://github.com/dchernykh1984/ChronometerPython/commit/a04c32b9aa73fc7e00f99e3ccad81a3c0cbd9478))

## [0.4.1](https://github.com/dchernykh1984/ChronometerPython/compare/v0.4.0...v0.4.1) (2026-11-15)


### Bug Fixes

* **firmware:** arm the beam only once its light has held, and say when it never does ([32f9345](https://github.com/dchernykh1984/ChronometerPython/commit/32f9345db649ba331a4c93dfe448fa1f39177f50))
* **firmware:** end the beam board's link on any reading error, so its port is opened again ([daaaba9](https://github.com/dchernykh1984/ChronometerPython/commit/daaaba97c02847a1d4294c04f163c6efcd016b02))
* **firmware:** end the beam connector once the program that started it is gone, so its port is free ([1260c22](https://github.com/dchernykh1984/ChronometerPython/commit/1260c2204f6eaa05a978f44059c23e8f8c331018))
* **firmware:** give up a write the beam board does not read within 1 s, so the connector never hangs on it ([0aaac7e](https://github.com/dchernykh1984/ChronometerPython/commit/0aaac7edf55a6faf6d7f6790fab80993494099bd))
* **firmware:** keep a beam break that comes before the board's HELLO or clock, timing it once both are known ([a7bb73f](https://github.com/dchernykh1984/ChronometerPython/commit/a7bb73f63095d6645b25af4d10e258600911d192))
* **firmware:** log a command the beam connector does not understand, as the protocol has it ([8e3566d](https://github.com/dchernykh1984/ChronometerPython/commit/8e3566d5851f7d556f15982f393f5ab1bab2fd3e))
* **firmware:** map the beam's breaks onto the computer's clock at once when that clock is set anew ([5074445](https://github.com/dchernykh1984/ChronometerPython/commit/5074445db349261bde9e1e117d7e6809abd41dfe))
* **firmware:** say which beam breaks never came, the board's count skipping them ([1344932](https://github.com/dchernykh1984/ChronometerPython/commit/134493281ea19d379320f3454faa853a04665965))
* **firmware:** stamp a beam break still waiting for the board's clock when the chronometer stops ([9cfb249](https://github.com/dchernykh1984/ChronometerPython/commit/9cfb249cf324f315cebbabca1642528bc6d497dc))
* **firmware:** take no line the beam board's port cut short as it ended ([25d5256](https://github.com/dchernykh1984/ChronometerPython/commit/25d5256dd53f4158429ccc178d35baae99b96286))


### Documentation

* **firmware:** say in main.py that the next beam break also waits for the light to be back ([4e7debb](https://github.com/dchernykh1984/ChronometerPython/commit/4e7debb4ccd4aff349b68226852ff71d026618ae))
* **firmware:** say the flickering light is reported after about 3 s, the board's second and the connector's two ([3967f03](https://github.com/dchernykh1984/ChronometerPython/commit/3967f03e85a57fad6fa84a6b6adae8a38668f7a1))
* **firmware:** say what a Mac and Linux ask before the beam board's port opens ([46f0126](https://github.com/dchernykh1984/ChronometerPython/commit/46f012633553aea049183da2ceb0c0d3d7be4861))
* list the beam board's folder in the project guide, and its tests outside the coverage gate ([2c518f0](https://github.com/dchernykh1984/ChronometerPython/commit/2c518f09339697323f963d512bbb624ac3e00dbe))
* **specs:** count a beam board's line only with its end, and say the breaks its count skips ([b64f496](https://github.com/dchernykh1984/ChronometerPython/commit/b64f4963f6b066e26b31d7f9d4bc469f3b4a81ac))
* **specs:** keep the beam board's lines in one contract, for the desktop connector and Android alike ([2d4d3d1](https://github.com/dchernykh1984/ChronometerPython/commit/2d4d3d1a4a0077ef7bb295541af5e9bca3a7d1b4))

## [0.4.0](https://github.com/dchernykh1984/ChronometerPython/compare/v0.3.0...v0.4.0) (2026-11-15)


### Features

* **firmware:** bring the beam board's breaks to the chronometer as a custom command ([6a296fc](https://github.com/dchernykh1984/ChronometerPython/commit/6a296fc058bfee2bb7490bf427b9b32e891f7c80))
* **firmware:** time each break of the light on the beam board itself ([83a62c4](https://github.com/dchernykh1984/ChronometerPython/commit/83a62c456daf6e8adb4716b35441ba57a0cd2e7e))


### Bug Fixes

* **firmware:** open the beam board's port exclusively, so a second program is refused, not given half its lines ([d5e9a2a](https://github.com/dchernykh1984/ChronometerPython/commit/d5e9a2a0cb532063873c63295e1f2d4c4d2491a2))
* **firmware:** pull the beam sensor's input up, so a loose wire reads as a blocked beam, not as noise ([6322f87](https://github.com/dchernykh1984/ChronometerPython/commit/6322f877e8f5623a8f892c1ab706edfd6154216d))
* **firmware:** refuse a beam hold-off outside 1 to 60000 ms at start, where the log shows it ([7ab8375](https://github.com/dchernykh1984/ChronometerPython/commit/7ab8375b53f5a4e298a7d6d5c0d8798c76cee668))
* **firmware:** say the beam board is gone when it answers no ping, its port still open ([f91daa0](https://github.com/dchernykh1984/ChronometerPython/commit/f91daa0f75c84b983b68fd7dc7339dd5eef90281))
* **firmware:** say when the beam board runs another firmware than the main.py beside the connector ([9bb04f4](https://github.com/dchernykh1984/ChronometerPython/commit/9bb04f46c47a7cd188476e75a1830cf196dfae70))
* **firmware:** say when the beam has been blocked longer than a rider takes, no break then to be seen ([e17fe25](https://github.com/dchernykh1984/ChronometerPython/commit/e17fe25f015d91d6750d341fb5511221ec499d13))
* **firmware:** take only a MicroPython RP2040 port for the beam board, not any Raspberry Pi device ([9ff6f29](https://github.com/dchernykh1984/ChronometerPython/commit/9ff6f29289524954bfb4ca60eeb5faf3a73ea2a9))


### Documentation

* **firmware:** fetch the beam connector's Python and pyserial once at home, so the race needs no network ([026ba5a](https://github.com/dchernykh1984/ChronometerPython/commit/026ba5a9162671476869a8b97a98751d88ac9057))
* **firmware:** say how to wire, flash and start the beam board, every version pinned ([2aaa6ad](https://github.com/dchernykh1984/ChronometerPython/commit/2aaa6ad9586acbf3079057e9f07f1265577afed4))
* **specs:** list the beam board this branch adds as a task, before the field test ([92c83d2](https://github.com/dchernykh1984/ChronometerPython/commit/92c83d21ace10dfbec3ed84c5b158a169aac8d43))
* **specs:** require the real beam to ride out a laser wavering in the wind or on a flexing ramp ([889dcaa](https://github.com/dchernykh1984/ChronometerPython/commit/889dcaa3d6ea0d88d19d0d0210d2d0768f5d4f96))

## [0.3.0](https://github.com/dchernykh1984/ChronometerPython/compare/v0.2.3...v0.3.0) (2026-11-07)


### Features

* offer to save the race config when closing with groups or paths not saved ([ff5d4dd](https://github.com/dchernykh1984/ChronometerPython/commit/ff5d4ddadc7c75ca3a93b47503fe4e6f0d6af5aa))
* save the race config to data/groupsList.txt with a button beside Load race config ([d260e42](https://github.com/dchernykh1984/ChronometerPython/commit/d260e4218970a334b8577db03dd461cb073e6b58))


### Bug Fixes

* keep Get groups from saving a race config with one file for both, by Save's rule ([76ff034](https://github.com/dchernykh1984/ChronometerPython/commit/76ff034037ebad4fdfa4b02ad95e542e367a9d45))
* keep the race config's groups apart from the start dropdown, which drops a group once started ([8a636f6](https://github.com/dchernykh1984/ChronometerPython/commit/8a636f620f8b55f409c69677654f0edb5ea7106a))
* make Cancel the reminder's default, so Enter after a close by mistake keeps the timing ([bc62469](https://github.com/dchernykh1984/ChronometerPython/commit/bc624693bcd387b907a0bcae77eac7c89462f1a7))
* make No the default of Are you sure to exit, so Enter after a close by mistake keeps the timing ([1ef0ede](https://github.com/dchernykh1984/ChronometerPython/commit/1ef0edeb705fa4b79e0d746c4459ee3c50a87304))
* read a race config path with a space after it as the same path the window shows ([c2ef0e5](https://github.com/dchernykh1984/ChronometerPython/commit/c2ef0e51174214822390481be16e854ca11d7cf2))
* refuse to save a race config with one file for both results and group starts ([307c3a8](https://github.com/dchernykh1984/ChronometerPython/commit/307c3a80baddd67efa70df7fa255e4a6740257fa))
* say only what is known when the race config cannot be saved at exit, no reason promised ([7d11866](https://github.com/dchernykh1984/ChronometerPython/commit/7d11866c5ddea15a5e4e6847a34d0077a96cda78))
* say why the window stays open when the race config cannot be saved at exit ([31e6f04](https://github.com/dchernykh1984/ChronometerPython/commit/31e6f0451943b712b21b4020bd85f9f69549a616))
* take a race config that cannot be read at exit as not saved, so the close goes on ([c2c3ec9](https://github.com/dchernykh1984/ChronometerPython/commit/c2c3ec97d13f7b4d49f9aa4e7e0580230c2c3663))
* tell one file spelled two ways by one rule, as the config reads paths back, for Save and the pickers ([fe6f1fc](https://github.com/dchernykh1984/ChronometerPython/commit/fe6f1fc30868489019e31bc2711ccdfa77bfd4a9))

## [0.2.3](https://github.com/dchernykh1984/ChronometerPython/compare/v0.2.2...v0.2.3) (2026-11-07)


### Bug Fixes

* **ci:** restore the macos release asset, lost to a retired runner label ([eb4ca40](https://github.com/dchernykh1984/ChronometerPython/commit/eb4ca402aa441d42b1df3eaa9c94b1fd160123ed))

## [0.2.2](https://github.com/dchernykh1984/ChronometerPython/compare/v0.2.1...v0.2.2) (2026-11-05)


### Bug Fixes

* flip the clock as each second starts, so it shows the second a stamp gets ([0de6f54](https://github.com/dchernykh1984/ChronometerPython/commit/0de6f54d2f0c398f91c4608adeea837ff480ed97))
* keep the clock ticking after a tick that fails, as it sets each next tick itself ([b4a5bb4](https://github.com/dchernykh1984/ChronometerPython/commit/b4a5bb4304cf0c5ed36ccf3a38dc591bf36da28f))
* show a clock that cannot be read as such, and say so in the log once ([6a1cbd5](https://github.com/dchernykh1984/ChronometerPython/commit/6a1cbd5ab2178f725996900d23533c0425727750))
* show the summer hour on the clock as soon as it is checked, as stamps get it ([280b4b0](https://github.com/dchernykh1984/ChronometerPython/commit/280b4b08c530a78624cde26233c017fcb00ec814))


### Documentation

* say the clock comes back within a tick after the clock is set, not at once ([b5b08f1](https://github.com/dchernykh1984/ChronometerPython/commit/b5b08f13ca2e3b95cf7b2e911e72b469377587e1))
* say the clock shows a hand stamp's second, a device's own rounded as before ([751c9a4](https://github.com/dchernykh1984/ChronometerPython/commit/751c9a44af06bf5d90b1d79f77070b16c5bc6eec))
* say why the summer box is connected to the clock where the clock's timer is made ([a165a69](https://github.com/dchernykh1984/ChronometerPython/commit/a165a693363c45dff405ac762fcede2191f2e86b))
* **skills:** say the clock ticks on a precise timer at each second, not a 1 ms one ([02e87a8](https://github.com/dchernykh1984/ChronometerPython/commit/02e87a83dc01db781750d541fc3b629d48291b8a))

## [0.2.1](https://github.com/dchernykh1984/ChronometerPython/compare/v0.2.0...v0.2.1) (2026-11-02)


### Bug Fixes

* back a DSQ and every key that writes a crossing up at once ([2452279](https://github.com/dchernykh1984/ChronometerPython/commit/24522799cee15db334b62dae89183d5b6ff9d4ec))
* back a group start time typed by hand up within 2 s ([ab6161b](https://github.com/dchernykh1984/ChronometerPython/commit/ab6161be77cd409b47266c862604b5ebeeae49ca))
* back a group up that the groups file refused ([1938583](https://github.com/dchernykh1984/ChronometerPython/commit/1938583cb3b7e69b3a883bd8dd8a6155e5cd74e3))
* back a number given to a stamped slot up as Enter is pressed ([013049c](https://github.com/dchernykh1984/ChronometerPython/commit/013049c5dceb324d7760681062dff27c0e1c11b9))
* back a saved group up with its line, not before it is written ([fbd2c49](https://github.com/dchernykh1984/ChronometerPython/commit/fbd2c496a5c82b316016a425b7fc585be3f981a8))
* back a second judge's Enter up only when it writes slot 1 ([6793d65](https://github.com/dchernykh1984/ChronometerPython/commit/6793d65c19d2460dc3e8146045f425db0b65073d))
* back a slot time typed or corrected by hand up within 2 s ([6c5f0a8](https://github.com/dchernykh1984/ChronometerPython/commit/6c5f0a8ce99dcd5a6dbbfaef18a29ed1affc47dd))
* back a stamped slot's number up however the judge leaves the field ([29aad73](https://github.com/dchernykh1984/ChronometerPython/commit/29aad73760b1a2055a003ef930733fb797e00cd1))
* back the slots up before Empty all clears them ([2259658](https://github.com/dchernykh1984/ChronometerPython/commit/2259658b969dc3a3c35ca7397205354517fa637b))
* bring a failed backup's later try forward when crossings come ([a3503d3](https://github.com/dchernykh1984/ChronometerPython/commit/a3503d36da565284b5116f0d86105ac9eb056238))
* bring forward only a try much later than a burst's own wait, so a stream never puts it off ([2ee169d](https://github.com/dchernykh1984/ChronometerPython/commit/2ee169d44443c4b5d2e5e002c803943de5900559))
* **chips:** back the log and the slots up after chip crossings ([2ea51e4](https://github.com/dchernykh1984/ChronometerPython/commit/2ea51e40cbdda23a55f728f9d0d31c30a0c65ae5))
* **chips:** log and back up every chip crossing that waits for the results file ([862220d](https://github.com/dchernykh1984/ChronometerPython/commit/862220de2ce7c46d8bd82391d2479ad696ccd566))
* **chips:** log once and back up every waiting crossing, one restored at a start too ([d4bab46](https://github.com/dchernykh1984/ChronometerPython/commit/d4bab467f0fdf22535f4642722f1b6dbf35782cc))
* **crossings:** back the log and the slots up after a correction ([01b763b](https://github.com/dchernykh1984/ChronometerPython/commit/01b763bc9590d4d293e747221ef05c0a221b20e2))
* empty no slots that could not be backed up first ([3dbee13](https://github.com/dchernykh1984/ChronometerPython/commit/3dbee13122e455934adb70d5c32f785e139d41eb))
* keep a second backup taken in the same second beside the first ([6bda49b](https://github.com/dchernykh1984/ChronometerPython/commit/6bda49bc8e6e124db46c6b16066b89e926f613e9))
* let Empty all schedule no backup of the slots it has just emptied ([c36c1fe](https://github.com/dchernykh1984/ChronometerPython/commit/c36c1fe2e52f03deb909f2c1d2a344f02b0ab4bc))
* **models:** put the slots backup on the disk before it takes its name ([bd7b056](https://github.com/dchernykh1984/ChronometerPython/commit/bd7b056ea06eaa9b778c44394dbf5c01b6c7866d))
* **models:** write the slots backup in one step, so a cut write leaves no backup ([44703cb](https://github.com/dchernykh1984/ChronometerPython/commit/44703cb36de6ccd2ae7ce33d875b8d89f2ed3c6e))
* **models:** write the slots backup unsynced and unwaited, so no hand stamp is late ([6937f99](https://github.com/dchernykh1984/ChronometerPython/commit/6937f9933ad0c73b133eccb582b283d1555ff0c5))
* number backups of one second so their names sort as they were taken ([0e86af8](https://github.com/dchernykh1984/ChronometerPython/commit/0e86af8d2b704cceb6cdaa85f68a6f06d957f262))
* say a backup that cannot be written in the action log ([4f4b0f1](https://github.com/dchernykh1984/ChronometerPython/commit/4f4b0f1260acb103c6b544053fc3602d79eb77ec))
* say how to empty slots that cannot be backed up ([620a224](https://github.com/dchernykh1984/ChronometerPython/commit/620a2241eeba7c4c5c984e81054be7792dea7691))
* say in the action log when backups are written again ([a02a696](https://github.com/dchernykh1984/ChronometerPython/commit/a02a696c951e77094221f53d56965a972d86f7b1))
* try a backup that could not be written again 2 s on ([0a4c167](https://github.com/dchernykh1984/ChronometerPython/commit/0a4c167f9347f00cfabfa63499aecde2459fd738))
* try a backup that keeps failing less often, up to once a minute ([f6423a2](https://github.com/dchernykh1984/ChronometerPython/commit/f6423a23d291098bf80f91a7fdffc1e1857afd17))
* try a failed backup again on a timer of its own, so no burst waits for it ([1613025](https://github.com/dchernykh1984/ChronometerPython/commit/161302520e3eb203fce4bdec499457e6c2ab5e06))
* write a backup waiting for its 2 s before the window closes ([2fe3529](https://github.com/dchernykh1984/ChronometerPython/commit/2fe352963918f1c6ca2dc9dfea0daeb9a467b8db))
* write the backup left out while backups were off once they are on again ([4c2aa38](https://github.com/dchernykh1984/ChronometerPython/commit/4c2aa386158569dd366e5ddf97aec1045774bb04))
* write the waiting backup on exit after the uploads have logged ([4da9886](https://github.com/dchernykh1984/ChronometerPython/commit/4da98863d0714272b104649cc8ef7f02077423f9))
* write the waiting backup on exit before the uploads, which log nothing more ([ab0df86](https://github.com/dchernykh1984/ChronometerPython/commit/ab0df864438a52dca972c9c4903d752039e427af))


### Performance Improvements

* let a backup written now take the place of one waiting to be ([c020f6b](https://github.com/dchernykh1984/ChronometerPython/commit/c020f6b94d725ee5e6bc087380f3d64eac6e0215))


### Documentation

* describe the slots backup as it now is: retried, before Empty all, numbered ([d561cea](https://github.com/dchernykh1984/ChronometerPython/commit/d561ceae0e5e8ea4ffedc52f2d85e41accbac750))
* list the review's backup work in the tasks and the backups in CLAUDE.md ([e05b339](https://github.com/dchernykh1984/ChronometerPython/commit/e05b339a2f34027bc428b339279b6e474a56b844))
* **models:** say what a power cut can leave of an unsynced backup ([6d9570b](https://github.com/dchernykh1984/ChronometerPython/commit/6d9570b9c0d709b0e79d7595fb4835b8dee102c6))
* say what the shared write point's backup is, and what a hand action adds ([7231e21](https://github.com/dchernykh1984/ChronometerPython/commit/7231e21994bbe8c4db287aefaeb6945561fa42fa))
* **specs:** back every crossing up as a hand crossing is ([0bc8839](https://github.com/dchernykh1984/ChronometerPython/commit/0bc88394962e0e0c0895e2b13fff9e77ee926042))
* **specs:** say how a failing backup is tried again and what Empty all keeps ([be87a3d](https://github.com/dchernykh1984/ChronometerPython/commit/be87a3d6daebb06ded8142d716fa4550f314d174))
* **specs:** say what clearing Disable backup writes and what typing backs up ([5c87fa2](https://github.com/dchernykh1984/ChronometerPython/commit/5c87fa2d8dcea8585ea99a133d9d01215e020d39))

## [0.2.0](https://github.com/dchernykh1984/ChronometerPython/compare/v0.1.9...v0.2.0) (2026-10-30)


### Features

* **beam:** stamp the first empty slot with each beam break and keep every break ([5f7a8a4](https://github.com/dchernykh1984/ChronometerPython/commit/5f7a8a42712e82aa9d7070945de4a5b36cf030ca))
* **chips:** list unknown chips and time them once the start protocol knows them ([64ca76e](https://github.com/dchernykh1984/ChronometerPython/commit/64ca76ef71b8f9d34db25fd28f17a192a07f3760))
* **chips:** map chips to bibs from the start protocol file ([638c6a6](https://github.com/dchernykh1984/ChronometerPython/commit/638c6a6cf6a9ef332cd2f32d5ea137d968e447b9))
* **chips:** report how many chips each rider's passes were read with ([5cc7513](https://github.com/dchernykh1984/ChronometerPython/commit/5cc75130932c3715593b0e0549993e944abbff4b))
* **chips:** turn chip reads into crossings with a dead time ([1fb0a64](https://github.com/dchernykh1984/ChronometerPython/commit/1fb0a64fc1b9e237ee544c3e1fddd081ff7b9e30))
* **connectors:** encode and decode the connector protocol ([01982b1](https://github.com/dchernykh1984/ChronometerPython/commit/01982b1a46f4aa70067a3b983c2c0b48361ec2d1))
* **connectors:** replay a chip reads file as a connector ([063df4c](https://github.com/dchernykh1984/ChronometerPython/commit/063df4c6e2708c8149f1e2c630cbdf7a220bd803))
* **connectors:** run test chips and test beam connectors from the chronometer itself ([99305a1](https://github.com/dchernykh1984/ChronometerPython/commit/99305a17f76094bc0c50aa061b86ea694a6241cd))
* **connectors:** start, watch and restart connector processes ([cb27096](https://github.com/dchernykh1984/ChronometerPython/commit/cb270966709e7c6a99cc383ed55e223839326f7c))
* **crossings:** add, edit and delete crossings of the results file ([ef87350](https://github.com/dchernykh1984/ChronometerPython/commit/ef8735022d1817e58f221035686084d2c87e7ce9))
* **crossings:** count a number's crossings from the results file ([52daa2d](https://github.com/dchernykh1984/ChronometerPython/commit/52daa2d9f0a88d8889b58cabc653e5de5fdc8094))
* **results:** rewrite the results file only after a backup of it ([e64bc5d](https://github.com/dchernykh1984/ChronometerPython/commit/e64bc5db0a5ee573cdf1cc116f823e47fcc53ed0))
* **site:** download the start protocol into its file by a button ([8c04376](https://github.com/dchernykh1984/ChronometerPython/commit/8c04376fad31853098059cc687cce031f44a9f19))
* **sources:** choose the event source and its connector ([414d14f](https://github.com/dchernykh1984/ChronometerPython/commit/414d14f671ee5171442b88fa4bed2d652ecb30fa))


### Bug Fixes

* **beam:** log a break that finds no slot and keep the focus where the judge types ([6c1db9b](https://github.com/dchernykh1984/ChronometerPython/commit/6c1db9b0c8064023e39a0787bbeb6848e0ffe743))
* **beam:** move full slots once per break and keep the focus on the number typed ([fa1f1dc](https://github.com/dchernykh1984/ChronometerPython/commit/fa1f1dc97e777ea6074b8aaa720ccc22c86af377))
* **beam:** move the slots on a break only while the judge types in one ([8bd2cd5](https://github.com/dchernykh1984/ChronometerPython/commit/8bd2cd5ca54c6354dd44c26d243744a31417b68c))
* **beam:** name in the log a slot written with no number to make room ([3ba0e9e](https://github.com/dchernykh1984/ChronometerPython/commit/3ba0e9e6cbd14417f1aae7925fcc6b4b62580b11))
* **beam:** never write slot 1 on a break before its number is typed ([6774724](https://github.com/dchernykh1984/ChronometerPython/commit/67747249fc9ce2038b4586de2ff84dfd131c063f))
* **beam:** never write slot 1 to make room while its number is typed, backing up once a burst ([6bf0718](https://github.com/dchernykh1984/ChronometerPython/commit/6bf071869e463d5dcc447bdde4ee5628d2260479))
* **beam:** never write slot 1 to make room while its time is corrected ([47fd7d8](https://github.com/dchernykh1984/ChronometerPython/commit/47fd7d8fc44db27ed40fae0e0cda801453ede70b))
* **chips:** count waiting chip crossings on the source's state line ([7e1ede5](https://github.com/dchernykh1984/ChronometerPython/commit/7e1ede5ecb0ce68d6cd02aa51535f3ef66556432))
* **chips:** download the start protocol into the file chosen when it was asked ([767957b](https://github.com/dchernykh1984/ChronometerPython/commit/767957b06ec1f5b363c528a205e1d24d07298fbd))
* **chips:** end a raw read a crash cut short before the next one is appended ([c8e25cf](https://github.com/dchernykh1984/ChronometerPython/commit/c8e25cfb5c6b475d5364fc317cf786d65d366ab3))
* **chips:** give newly bound reads no crossing where their pass already has one ([fec4d5e](https://github.com/dchernykh1984/ChronometerPython/commit/fec4d5e7bd17b950d3e6ba6e8234d0525fb867e6))
* **chips:** never retry a state left unsaved on a switch under the next file ([125945f](https://github.com/dchernykh1984/ChronometerPython/commit/125945f68bee3daf93358ffd400d8b10170aaa35))
* **chips:** rebuild the chips map after a download only from the file in use ([8b6695c](https://github.com/dchernykh1984/ChronometerPython/commit/8b6695c440fc71781abb2e879880b85ff8cf14c5))
* **chips:** rest the retry timer while its file is not in use, retry when it is ([f1b386c](https://github.com/dchernykh1984/ChronometerPython/commit/f1b386c4a9d7b0ba0a98bb1fe28e89aed23f197c))
* **chips:** save the chip state as soon as a retry writes waiting crossings ([6ce855f](https://github.com/dchernykh1984/ChronometerPython/commit/6ce855fa3ae032b94785adf9d42bfefd7dd2dc55))
* **chips:** save the chip state on time while reads keep coming ([f597e67](https://github.com/dchernykh1984/ChronometerPython/commit/f597e67cb24611f7e246b2a1a157fa2e8518c328))
* **chips:** save the chip state with retries and rebuild it after a crash or another race ([3610529](https://github.com/dchernykh1984/ChronometerPython/commit/3610529170e58adbd7321af48ffbaa6bb55fad64))
* **chips:** sort a bib like 1-squared in the chip report instead of failing ([8aebfdd](https://github.com/dchernykh1984/ChronometerPython/commit/8aebfdd794db3d9365c36431fa3a1932ee16b187))
* **chips:** write the chip state safely and rebuild a lost one from the raw reads ([d2626ee](https://github.com/dchernykh1984/ChronometerPython/commit/d2626eeb681f0b260c17b6b6cfec4c5d1df1dd38))
* **chips:** write waiting crossings only into the results file they belong to ([cc4ae01](https://github.com/dchernykh1984/ChronometerPython/commit/cc4ae0109a294662502054f5454da9555df2ec05))
* **crossings:** apply a correction to the results file as it is after the dialog ([11a70eb](https://github.com/dchernykh1984/ChronometerPython/commit/11a70ebe3174718f55ed80b3d7c58383b234ba99))
* **crossings:** count crossings beside the slots from the results file just chosen ([400e9b3](https://github.com/dchernykh1984/ChronometerPython/commit/400e9b37f65e8a93d9856c3172b4bcf90b269e08))
* **crossings:** end rewritten lines as appended ones are and read the file with the shared reader ([9006fe5](https://github.com/dchernykh1984/ChronometerPython/commit/9006fe564a97cfa424c709a11b2e1efd0b998179))
* **crossings:** note a written line in one place and leave no temporary file after a failed write ([1751e29](https://github.com/dchernykh1984/ChronometerPython/commit/1751e2902400333640b6b205b14ce160cbd2b804))
* **crossings:** read a folder typed on the way to the results file as no file ([d7b7484](https://github.com/dchernykh1984/ChronometerPython/commit/d7b7484a87d65d8f1691e711963244b8d052c956))
* **crossings:** read old cp1251 and new UTF-8 lines of one file each as written ([3ca3b45](https://github.com/dchernykh1984/ChronometerPython/commit/3ca3b452ee7d5371c24108f262f2f9664ab73f28))
* **crossings:** refuse a number or action with any line break Python splits at ([86162f6](https://github.com/dchernykh1984/ChronometerPython/commit/86162f6ec5e89e4ce7a7f80b705c107d0a3cadfe))
* **crossings:** take times in ASCII digits only and keep a line's later fields on an edit ([496c6c2](https://github.com/dchernykh1984/ChronometerPython/commit/496c6c2af1e31d538e97d62aa339c037116f19f8))
* **models:** drop a byte order mark before decoding, so a cp1251 first line loses it too ([00954e4](https://github.com/dchernykh1984/ChronometerPython/commit/00954e4302cb0e334945c0bdfcd6b3e7d8e164cd))
* **site:** load the groups off the UI thread, as the start protocol download is ([28ff90d](https://github.com/dchernykh1984/ChronometerPython/commit/28ff90d1a6f02eb8b1c0eb7a4d6bdc7b7c4edff3))
* **site:** refuse groups and start list answers not shaped as the site sends them ([a894ff9](https://github.com/dchernykh1984/ChronometerPython/commit/a894ff9d2565e1024495f5e0b464709fcaeff669))
* **site:** report upload failures as downloads do, through one request helper ([d91efed](https://github.com/dchernykh1984/ChronometerPython/commit/d91efed6355472a300d551151bdae0ab956688a5))
* **site:** share one GET helper that reports a read timeout as a connection error ([6dc2311](https://github.com/dchernykh1984/ChronometerPython/commit/6dc2311f966fa2655b2620c169615854baaca8bc))
* **sources:** count a steady run from the hello and drop an overlong connector line early ([be63b2a](https://github.com/dchernykh1984/ChronometerPython/commit/be63b2aa69cb0d801a9b2e726263790694f9ff30))
* **sources:** count a stopped connector's last line and reports until it has ended ([62105c3](https://github.com/dchernykh1984/ChronometerPython/commit/62105c35e4da2821dc956a7fe113f86d3e905450))
* **sources:** freeze the file paths while a device runs and show late site answers in the log ([05a2fae](https://github.com/dchernykh1984/ChronometerPython/commit/05a2fae31ae13059460bfb4fd6a84e18f8f7df97))
* **sources:** handle what a connector sent before a stop or restart, a late hello included ([2cbceed](https://github.com/dchernykh1984/ChronometerPython/commit/2cbceedaa6bbdf846216df48959f32eea4ce5a09))
* **sources:** have the test and replay connectors say what is wrong with their settings ([5c99f18](https://github.com/dchernykh1984/ChronometerPython/commit/5c99f1883b02f17336bb7d478168ac8b824dfae5))
* **sources:** ignore a connector line of another type and round an event time to the millisecond ([8a26f3e](https://github.com/dchernykh1984/ChronometerPython/commit/8a26f3ee4d221ff1fe9d7ecc071cfb41a06cb6a5))
* **sources:** keep a custom command for the beam and another for chips ([41b61c8](https://github.com/dchernykh1984/ChronometerPython/commit/41b61c83441f95d94c9fed55057964e0f0d9b9f6))
* **sources:** keep device text and DSQ reasons on one line by every line break ([eb47d0b](https://github.com/dchernykh1984/ChronometerPython/commit/eb47d0be7a17fecd988ca6f4e053baff2cdeb73c))
* **sources:** keep the device files of finish, finish.txt, finish.day1 and finish.day2 apart ([561bfe5](https://github.com/dchernykh1984/ChronometerPython/commit/561bfe5c2e7a03e527478ee141cabbd580f583f3))
* **sources:** keep the settings typed for a device when another is picked ([92c2cea](https://github.com/dchernykh1984/ChronometerPython/commit/92c2cea8432d0fa904d3b13cc743a7143319557d))
* **sources:** let a connector wait out an endless pause instead of failing ([6f973a7](https://github.com/dchernykh1984/ChronometerPython/commit/6f973a70bb90ffc8f958db9c080fcdde9f908dab))
* **sources:** load no race config while a device runs ([c157119](https://github.com/dchernykh1984/ChronometerPython/commit/c1571196b6f026e497b6e6fea33cfd7014b813a7))
* **sources:** log a connector's error output once a run, briefly, a repeat in one line ([ab6b8e8](https://github.com/dchernykh1984/ChronometerPython/commit/ab6b8e839caa8b666f9cfe5b30657188c81067b6))
* **sources:** read data/sources.txt safely, a bad dead time as the default, and write it at once ([8f27f9f](https://github.com/dchernykh1984/ChronometerPython/commit/8f27f9fb8d7714e5a18b208fe3fb3b6fec4b5390))
* **sources:** refuse an event time before 2000, a device clock never set ([29e3a10](https://github.com/dchernykh1984/ChronometerPython/commit/29e3a105c88efe1dc3dfabbbaa9a90b31f681c96))
* **sources:** refuse an event time out of range and pass on only the source's own kind of events ([3098c49](https://github.com/dchernykh1984/ChronometerPython/commit/3098c49922c3f437a4050e8622bdcfe5ef967f15))
* **sources:** run a connector in the folder the event's data is in ([8f153dd](https://github.com/dchernykh1984/ChronometerPython/commit/8f153dd18cc3251826f20ca3c641b635a815a8cd))
* **sources:** start a device only once a results file is chosen ([3fb8da4](https://github.com/dchernykh1984/ChronometerPython/commit/3fb8da41926db9331ddcb3c9024a4f15f4b052f0))
* **sources:** start with the settings and start protocol path as typed, Return pressed or not ([6d725e6](https://github.com/dchernykh1984/ChronometerPython/commit/6d725e63c3c57f09b0cc4400a260a43b1cf835ba))
* **sources:** stop for good a program with a wrong hello and handle what it sent before a stop ([9798f0f](https://github.com/dchernykh1984/ChronometerPython/commit/9798f0f2de85225523fdae7c08bb96378ec9b6c6))
* **sources:** treat a stopped device as running and lock its choices until its program ends ([a61e0a8](https://github.com/dchernykh1984/ChronometerPython/commit/a61e0a82e9ca49c4572dcd6bd52c44cf903c068b))
* **sources:** use nothing more a program sends once its hello is refused ([272a2bf](https://github.com/dchernykh1984/ChronometerPython/commit/272a2bfbd2bbf3a096e22fe5b3e2515b22d087fa))
* **sources:** wait 30 s for a connector's hello and let a stopped one exit in its own time ([4d7655e](https://github.com/dchernykh1984/ChronometerPython/commit/4d7655e8ce7a9760c622fc83610278162ccf0f65))


### Performance Improvements

* **chips:** keep the reads of an unbound chip as runs, not one by one ([c12da62](https://github.com/dchernykh1984/ChronometerPython/commit/c12da6268633078e065a53a707936ed85761302d))
* **chips:** refresh the unknown chips list at most twice a second ([400311e](https://github.com/dchernykh1984/ChronometerPython/commit/400311eaa68b18e38196858482c49d2177811094))
* **chips:** save the chip state at most once a second, not for every crossing ([1a7b9e8](https://github.com/dchernykh1984/ChronometerPython/commit/1a7b9e8afafbe840a0eab405222d5fd50e3f4ae3))
* **chips:** save the chip state without an fsync, compactly, as it is rebuilt if lost ([7ec02cb](https://github.com/dchernykh1984/ChronometerPython/commit/7ec02cbb576ce818a60d838719af323dda6eeec1))
* **chips:** try a chip state save once rather than wait for a held file ([85e6afe](https://github.com/dchernykh1984/ChronometerPython/commit/85e6afefc3997a8a274b355fc0bc5bfcec96fcb5))
* **crossings:** keep the results file's lines only where shown and read them once a path is typed ([40cd972](https://github.com/dchernykh1984/ChronometerPython/commit/40cd97291d148cab9798ce473bb757dbd981aa60))
* **crossings:** wait at most 0.5 s for a results file another program holds ([e76c935](https://github.com/dchernykh1984/ChronometerPython/commit/e76c935bb2ef6789d7ae4b52dd7a6274c30e7cfd))


### Documentation

* adopt a constitution for spec-first changes ([3939e5f](https://github.com/dchernykh1984/ChronometerPython/commit/3939e5f411eab30501f0870b9aaf81fc9e29245e))
* describe event sources, corrections and the chip files ([421a62d](https://github.com/dchernykh1984/ChronometerPython/commit/421a62d5150094c8eb0d4ca6decc8162f50e4c72))
* describe the chronometer as it works today ([dc50169](https://github.com/dchernykh1984/ChronometerPython/commit/dc50169dce891dab6eb0edbcbc6cd3e0f6e10848))
* name Spec Kit's generated files among the exceptions to the ASCII rule ([602f334](https://github.com/dchernykh1984/ChronometerPython/commit/602f3342d19e9c30ce8fe3d99a42d03f32e11697))
* plan event sources, the connector protocol and the chip files ([6998897](https://github.com/dchernykh1984/ChronometerPython/commit/6998897ba102773bfd38a275f8c48a4a68ba041f))
* settle the event source spec, plan and tasks after three review cycles ([0095c92](https://github.com/dchernykh1984/ChronometerPython/commit/0095c92ef6a8b05e0664b65d4adbba415784ecab))
* specify event sources by hand, light beam and timing chips ([f5ed789](https://github.com/dchernykh1984/ChronometerPython/commit/f5ed789fb4cd591fcf46d70c5c7bbab304602ec6))

## [0.1.9](https://github.com/dchernykh1984/ChronometerPython/compare/v0.1.8...v0.1.9) (2026-10-11)


### Bug Fixes

* resolve runtime files beside the portable application ([8f0afd8](https://github.com/dchernykh1984/ChronometerPython/commit/8f0afd853ad771367387d4b2f180d4c254f271c4))


### Documentation

* clarify portable runtime paths for coding agents ([96e9086](https://github.com/dchernykh1984/ChronometerPython/commit/96e9086cff5436c8f9cb01fda1269996b68d30e3))

## [0.1.8](https://github.com/dchernykh1984/ChronometerPython/compare/v0.1.7...v0.1.8) (2026-09-04)


### Documentation

* take the CI verdict from the rollup, not the lagging checks list ([ca79eb4](https://github.com/dchernykh1984/ChronometerPython/commit/ca79eb4c01960b16440a916499287a6f6fea1ca5))

## [0.1.7](https://github.com/dchernykh1984/ChronometerPython/compare/v0.1.6...v0.1.7) (2026-09-03)


### Documentation

* add a claude guide for the project ([a49c5c9](https://github.com/dchernykh1984/ChronometerPython/commit/a49c5c9cf8a801c0b7615ebb625b0874cfc1a424))

## [0.1.6](https://github.com/dchernykh1984/ChronometerPython/compare/v0.1.5...v0.1.6) (2026-08-28)


### Bug Fixes

* keep the group start time after saving a group ([736f8c0](https://github.com/dchernykh1984/ChronometerPython/commit/736f8c009fd2358d49b15af32be24075afccaefd))

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
