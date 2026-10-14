| arm | pairs detected /22 | recovered vs B0 | lost vs B0 | showcase pairs /14 | FA/min whole clip (provisional) | FA/min verified review windows | FA/min union windows | mixed-scene extra-class clips | TTFC proxy p50 / p90 s | births/min (pos) | label changes / track-min | Kaggle CPU p50 / p95 ms | verifier calls / frame |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B0 | 11/22 | - | - | 7/14 | 2.859 (104 tr, 36.37 min) | 2.855 (9 tr, 3.15 min) | 5.607 (23) | 9 | 2.24 / 28.11 | 34.63 | 3.873 | 162.3 / 191.6 | 0.0 |
| B1 | 12/22 | #11 carrot | - | 8/14 | 4.069 (148 tr, 36.37 min) | 3.49 (11 tr, 3.15 min) | 4.876 (20) | 8 | 14.02 / 30.97 | 33.82 | 3.485 | 161.4 / 186.5 | 0.0 |
| B2 | 11/22 | - | - | 7/14 | 1.54 (56 tr, 36.37 min) | 2.221 (7 tr, 3.15 min) | 3.901 (16) | 9 | 2.24 / 28.11 | 32.48 | 4.154 | 162.4 / 192.2 | 0.031 |

| class | B0 | B1 | B2 |
|---|---|---|---|
| apple | 1/2 | 1/2 | 1/2 |
| banana | 3/4 | 3/4 | 3/4 |
| capsicum | 1/1 | 1/1 | 1/1 |
| carrot | 1/4 | 2/4 | 1/4 |
| citrus | 2/3 | 2/3 | 2/3 |
| cucumber | 1/1 | 1/1 | 1/1 |
| lemon_lime | 1/2 | 1/2 | 1/2 |
| mango | 1/3 | 1/3 | 1/3 |
| potato | 0/1 | 0/1 | 0/1 |
| tomato | 0/1 | 0/1 | 0/1 |

Uploader-level bootstrap (1000), arm - B0:
- B1_vs_B0 (all12): recall diff CI95 [0.0, 0.182], FA/min diff CI95 [-0.283, 1.74] (25 uploaders)
- B1_vs_B0 (show5): recall diff CI95 [0.0, 0.273], FA/min diff CI95 [-0.237, 1.322] (24 uploaders)
- B2_vs_B0 (all12): recall diff CI95 [0.0, 0.0], FA/min diff CI95 [-1.483, -0.352] (25 uploaders)
- B2_vs_B0 (show5): recall diff CI95 [0.0, 0.0], FA/min diff CI95 [-1.448, -0.338] (24 uploaders)

Per negative clip FA tracks (all12, B0/B1/B2): #6 c8b2d2f36 0/0/0; #7 c0a13587f 71/100/33; #10 c3cc14a1f 1/0/0; #12 c87e3900a 0/0/0; #13 c94ab39f5 0/5/0; #14 c973b3f44 0/0/0; #15 c97e354bf 10/10/9; #17 cb05e346c 0/0/0; #20 cfe0b39f1 9/11/5; #26 c0a08d565 1/3/1; #27 c3d854faf 2/1/0; #29 c4e9a7195 3/1/3; #30 c6f5ac9b4 2/1/2; #32 cc5585ebc 0/0/0; #33 cd17ce723 5/14/3; #34 ce9f2fe34 0/2/0

Mixed-scene extra classes (shown >= 0.5 s on verified-positive clips, class not in truth): B0: #1 potato, #3 apple/carrot, #4 banana/lemon_lime, #5 banana, #11 apple/banana, #18 apple, #22 apple/banana, #24 apple/banana, #25 apple/banana/cucumber; B1: #3 apple/lemon_lime, #4 banana/lemon_lime, #5 banana, #11 banana/cucumber, #21 citrus, #22 apple/banana, #24 apple/banana/cucumber, #25 apple/banana; B2: #1 potato, #3 apple/carrot, #4 banana/lemon_lime, #5 banana, #11 apple/banana, #18 apple, #22 apple/banana, #24 apple/banana, #25 apple/banana/cucumber
