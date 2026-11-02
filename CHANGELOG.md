# Changelog

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
