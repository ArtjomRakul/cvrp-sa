# CVRP ar simulēto rūdīšanu (CVRP + SA)

Mazais praktiskais darbs kursā *Praktiskā kombinatoriālā optimizācija* (LU, 2026).

**Uzdevums:** kapacitātes ierobežotā transportlīdzekļu maršrutēšanas problēma (CVRP) - no
noliktavas jāapkalpo visi klienti ar mašīnām, kuru ietilpība ir ierobežota, minimizējot
kopējo nobraukto attālumu.
**Algoritms:** simulētā rūdīšana (SA); salīdzinājumam kalnā kāpšana (HC) ar to pašu apkārtni.
Viss implementēts no nulles tīrā Python (tikai standarta bibliotēka, bez gatavām optimizācijas
bibliotēkām). Nekas nav jāinstalē; `matplotlib` vajadzīgs tikai maršrutu attēlam (`run.py --plot`).

## Struktūra

```
cvrp/
  instance.py      DOMĒNS: problēmas fakti, CVRPLIB (.vrp/.sol) nolasīšana
  evaluation.py    NOVĒRTĒŠANA: hard (pārkrāvums) / soft (attālums) + neatkarīgs pārbaudītājs
  moves.py         GĀJIENS: relocate / swap / 2-opt / 2-opt* ar O(1) delta novērtēšanu
  construction.py  sākotnējais risinājums (tuvākā kaimiņa heiristika)
  algorithms.py    ALGORITMS: simulētā rūdīšana un kalnā kāpšana
instances/         8 CVRPLIB testa instances (.vrp) ar optimālajiem risinājumiem (.sol)
instances/calibration/  2 citas CVRPLIB instances SA parametra kalibrēšanai
results/           rezultāti: runs.csv, summary.csv/md, calibration.csv/md, environment.json
tests/             pareizības testi
run.py             vienas instances risināšana
experiments.py     pilnā testēšana;  calibrate.py - SA sākuma temperatūras kalibrēšana
```

## Kā pārbaudīt darbu

Vajag tikai Python 3 (pārbaudīts ar 3.13 un 3.14), nekas nav jāinstalē. Komandas palaiž no
repozitorija saknes mapes (tur, kur ir `experiments.py`).

**1. Pareizības testi** (~5 s): katra gājiena ātri aprēķinātā izmaiņa sakrīt ar pilno pārrēķinu,
un publicētie CVRPLIB optimālie risinājumi mūsu modelī dod tieši publicēto attālumu.
```
python -m tests.test_moves
```

**2. Viena instance** (~3 s): SA atrisina A-n32-k5 un atrod optimumu 784.
```
python run.py instances/A-n32-k5.vrp
```

**3. Atskaites rezultātu atkārtošana** (~15-30 min, 1 CPU kodols): visas 8 instances, SA un HC,
pa 5 sēklām. Rezultāti tiek saglabāti atsevišķā mapē, lai tos varētu salīdzināt ar `results/`.
```
python experiments.py --out results_check
```
Sēklas ir fiksētas, tāpēc `results_check/summary.md` attālumi (risinājumu kvalitāte) sakrīt ar
`results/summary.md` un atskaites 1. tabulu; atšķiras tikai izpildes laiki (dators un Python
versija tiek ierakstīti `environment.json`). Ja nav laika pilnajai testēšanai,
`python experiments.py --quick --out results_quick` (~1 min) pārbauda, ka viss darbojas, bet ar
10x mazāku budžetu un 2 sēklām, tāpēc tās rezultāti ir sliktāki.

### Google Colab

```
!git clone https://github.com/ArtjomRakul/cvrp-sa
%cd cvrp-sa
!python -m tests.test_moves
!python run.py instances/A-n32-k5.vrp
!python experiments.py --out results_check
```

## Citas komandas (neobligāti)

```
python run.py instances/X-n101-k25.vrp --alg hc --seed 3   # cits algoritms (sa / hc) un sēkla
python calibrate.py                                         # SA parametra p0 kalibrēšana (~5-10 min)
pip install -r requirements.txt                             # tikai maršrutu attēlam:
python run.py instances/X-n101-k25.vrp --plot marsruti.png
```

Pārtraukta `experiments.py` palaišana turpinās no `<out>/parts/`; lai rēķinātu no jauna,
izdzēsiet šo mapi.

## Testa piemēri

CVRPLIB instances ([PyVRP/VRPLIB](https://github.com/PyVRP/VRPLIB), MIT licence) ar publicētām
optimālajām / labākajām zināmajām vērtībām: P-n16-k8, A-n32-k5, F-n72-k4, M-n101-k10
(klasiskās, fiksēts K) un X-n101-k25, X-n120-k6, X-n157-k13, X-n200-k36 (Uchoa et al., 2017,
neierobežota flote). Attālumi: nint(eiklīda attālums), kā CVRPLIB. Kalibrēšanai - X-n110-k13
un X-n153-k22, kas nav testa kopā.
