| view | config | pairs | detected | clip presence recall | FA/min (neg, 36.37 min) | FA tracks | neg clips w/ class FA | TTFC proxy p50 / p90 s | births/min (pos) | tracks per detected pair | label changes / track-min |
|---|---|---|---|---|---|---|---|---|---|---|---|
| all12 | A0 | 22 | 11 | 0.5 | 2.859 | 104 | 4/16 | 2.24 / 28.11 | 34.63 | 43.18 | 3.873 |
| all12 | A1 | 22 | 9 | 0.409 | 2.034 | 74 | 4/16 | 21.94 / 46.62 | 28.93 | 43.56 | 0.836 |
| all12 | A2 | 22 | 9 | 0.409 | 0.88 | 32 | 4/16 | 22.02 / 47.09 | 25.2 | 39.0 | 0.924 |
| all12 | A3 | 22 | 10 | 0.455 | 1.512 | 55 | 4/16 | 7.53 / 37.64 | 29.8 | 42.1 | 4.301 |
| show5 | A0 | 14 | 7 | 0.5 | 2.612 | 95 | 3/16 | 2.24 / 43.8 | 31.61 | 59.57 | 1.207 |
| show5 | A1 | 14 | 6 | 0.429 | 1.897 | 69 | 3/16 | 12.21 / 72.56 | 28.75 | 64.83 | 0.725 |
| show5 | A2 | 14 | 6 | 0.429 | 0.797 | 29 | 3/16 | 12.29 / 73.59 | 25.09 | 58.0 | 0.801 |
| show5 | A3 | 14 | 6 | 0.429 | 1.402 | 51 | 3/16 | 12.25 / 73.59 | 27.76 | 62.17 | 1.332 |

| class | A0 | A1 | A2 | A3 |
|---|---|---|---|---|
| apple | 1/2 | 1/2 | 1/2 | 1/2 |
| banana | 3/4 | 3/4 | 3/4 | 3/4 |
| capsicum | 1/1 | 1/1 | 1/1 | 1/1 |
| carrot | 1/4 | 0/4 | 0/4 | 0/4 |
| citrus | 2/3 | 2/3 | 2/3 | 2/3 |
| cucumber | 1/1 | 1/1 | 1/1 | 1/1 |
| lemon_lime | 1/2 | 0/2 | 0/2 | 1/2 |
| mango | 1/3 | 1/3 | 1/3 | 1/3 |
| potato | 0/1 | 0/1 | 0/1 | 0/1 |
| tomato | 0/1 | 0/1 | 0/1 | 0/1 |

Uploader-level bootstrap (1000), candidate - A0:
- A1_vs_A0 (all12): recall diff CI95 [-0.222, 0.0], FA/min diff CI95 [-1.459, -0.623] (25 uploaders)
- A1_vs_A0 (show5): recall diff CI95 [-0.286, 0.0], FA/min diff CI95 [-1.306, -0.447] (24 uploaders)
- A2_vs_A0 (all12): recall diff CI95 [-0.222, 0.0], FA/min diff CI95 [-2.524, -1.117] (25 uploaders)
- A2_vs_A0 (show5): recall diff CI95 [-0.286, 0.0], FA/min diff CI95 [-2.064, -0.898] (24 uploaders)
- A3_vs_A0 (all12): recall diff CI95 [-0.182, 0.0], FA/min diff CI95 [-2.284, -0.763] (25 uploaders)
- A3_vs_A0 (show5): recall diff CI95 [-0.286, 0.0], FA/min diff CI95 [-1.83, -0.662] (24 uploaders)

Per negative clip FA tracks (all12): #6 c8b2d2f36 0/0/0/0; #7 c0a13587f 71/54/20/39; #10 c3cc14a1f 1/1/0/0; #12 c87e3900a 0/0/0/0; #13 c94ab39f5 0/0/0/0; #14 c973b3f44 0/0/0/0; #15 c97e354bf 10/8/4/4; #17 cb05e346c 0/0/0/0; #20 cfe0b39f1 9/4/3/5; #26 c0a08d565 1/0/0/1; #27 c3d854faf 2/1/0/1; #29 c4e9a7195 3/1/0/0; #30 c6f5ac9b4 2/1/1/1; #32 cc5585ebc 0/0/0/0; #33 cd17ce723 5/4/4/4; #34 ce9f2fe34 0/0/0/0 (A0/A1/A2/A3)
