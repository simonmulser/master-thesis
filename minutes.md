# 7.12.16
* mit klemen
* kurze vorstellung meinerseits, spezialisierungsbereiche, ideen
* mögliche themenbereiche
 * secure software development lifecycle (secure SDLC)
 * trusted code
 * mitarbeit bei einer security matrix (x-achse programmiersprache, y-achse typischer themenbereich)
 * blockchain, e-voting
* forschungsantrag TRUC
* folgetreffen mit weipl

# 18.01.17
* mit weipl
* themenbereiche bei blockchain
 * namecoin
 * merged mining
* dissertanten bei SBA
 * Nicholas Stifter
 * Aljosha Judmayer
* machstrukturen im bitcoin netzwerk
* was passiert wenn mining reward = 0
* migrationen von blockchains

# 18.01.17
* mit aljosha
* simulation
* momentan problem bei simulatio mit zfs laufwerk
* erstellen von accounts (gitlab, mattermost, ...)
* freischalten von repo mit wichtigen papers
* next steps
 * grundlegende papers lesen
 * thema überlegen

# 09.02.17
* mit aljosha, nicholas, andreas
* zfs thema besteht immer noch, erster task von simon
* ideen für DA
 * selfish mining (wird priorisiert)
 * eclipse attacks
* kleine recherche und einlesen in netzwerk simulations software (ns2, ns3)
* slicetime, als input wie man netzwerk simulation auch umsetzen kann
* simulation soll ohne großen aufwand auf ähnlichem oder stärkerm system reproduzierbar und deterministisch wiederholbar sein
* mit andreas zusammen setzen, nächstes meeting mit aljosha anfang märz

# 15.02.17
* mit andreas
* einführung und Q&A für simon
* andreas refactored den code weiter
 * DockerCommands
 * NetworkCommands
 * LogProcessing
 * lesbarkeit, naming
 * string concatenation besser lesbar machen
* btn = bitcoin testnetwork
* simon lest sich weiter ein
 * im bitcoin wiki werden viele befehle erklärt, client mal mit den commands ansprechen und system weiter verstehen
 * zfs reproduzieren und schauen ob problem besteht
* auch commands in den ELK stack füttern für eventuelles troubleshooting
* selfish minig könnte man mit einem proxy umsetzten der zwischen 2 nodes sitzt networkt <-> normal node <-> proxy, and only connections to <-> normal node with known IP
im proxy wird das selfish mining implementiert somit müsste man die referenz implementierungen nicht angreifen

# 06.03.17
* mit aljosha, nicholas, andreas
* erklärung und besprechung zfs
 * zfs funktioniert
 * zfs am host system hat dedup und recordsize 512bytes bereits aktiviert
* virtual machine (vm) mit simulation ausreizen und ertesten wo das bottle neck ist
* vm kann noch skaliert werden und notfalls können simulationen auch in der cloud ausgeführt werden
* simon implementiert proxy node
 * lesen der selfish mining papers mit den verschiedenen strategien
 * implementierung in python
 * so generisch wie möglich dh. verschieden selfish mining strategien und der proxy soll auch als eclipse attack node verwendet werden können
 * aljosha schickt relevante selfish mining papers als ausgangslage
* andreas refactored und implementiert simcoin für seine arbeit weiter
