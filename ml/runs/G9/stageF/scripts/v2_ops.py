# M-DEV v2 repair decisions (agent, review of native-pixel crowd crops with OWLv2 region proposals; no model predictions viewed)
D = {}
def add(I, *ops): D.setdefault(I, {"ops": []})["ops"].extend(ops)
add("m0024", ["keep", 0, "tomatoes ~20 px, heavy overlap; proposals fragmentary (~half coverage)"],
             ["keep", 1, "green bell peppers overlapping; proposals mix the tomato row above"],
             ["conv", 2, list(range(99))], ["addpx", 2, [[393,113,455,263],[445,110,518,263],[493,123,562,263],[535,140,640,283],[95,288,415,398],[190,353,500,478],[75,438,290,538],[215,473,440,543],[440,408,545,543],[540,388,710,498],[630,448,785,543],[645,303,770,388],[690,388,795,473],[255,208,460,353],[150,248,320,338]]],
             ["ignpx", 2, [[695,68,850,198]]], ["conv", 3, [30]])
add("m0024", ["keep", 4, "carrots tied in bunches, individual roots overlap heavily"])
add("m0059", ["conv", 0, list(range(99))], ["addpx", 0, [[82,122,172,186],[80,186,170,242],[85,242,155,304],[78,309,150,389],[255,116,378,174],[255,172,350,256],[280,299,355,369],[455,89,525,169],[425,169,535,249],[410,242,538,334]]],
             ["crowdpx", 0, [[130,369,765,489]]])
add("m0140", ["conv", 0, list(range(99))], ["addpx", 0, [[330,448,410,533],[420,438,520,528],[425,538,500,623],[335,528,390,593],[600,203,670,273],[525,298,590,368],[88,606,135,640],[160,613,240,660],[290,608,390,660],[515,478,565,538]]],
             ["ignpx", 0, [[560,40,740,190]]])
add("m0184", ["conv", 3, list(range(99))], ["addpx", 3, [[205,168,315,278],[315,178,420,288],[355,88,460,193],[420,178,530,278],[505,138,610,238],[150,263,240,363],[235,278,350,373],[350,263,475,368],[485,243,590,353],[570,228,660,323],[185,358,255,423],[235,363,345,463],[345,348,470,458],[475,338,590,438],[575,323,700,418],[450,108,510,178],[695,148,775,223],[685,218,780,303]]])
add("m0191", ["keep", 0, "3-4 banana hands inside a paper bag, overlapping; boundaries ambiguous"])
add("m0197", ["conv", 0, list(range(999))], ["addpx", 0, [[68,402,160,549],[155,399,265,549],[265,399,425,564],[425,399,500,559],[500,409,620,559],[75,284,260,389],[265,279,475,384],[475,339,630,404],[45,114,250,274],[160,44,355,144],[355,49,535,144]]],
             ["crowdpx", 0, [[250,144,835,299],[540,29,835,164]]],
             ["conv", 1, list(range(999))], ["addpx", 1, [[105,108,250,218],[240,108,390,223],[385,83,450,158],[480,78,660,223],[690,103,760,183]]])
add("m0220", ["convpx", 0, [105,48,460,213]], ["convpx", 0, [490,58,840,193]], ["crowdpx", 0, [[105,20,860,58]]], ["ignpx", 0, [[0,20,105,265]]])
add("m0220", ["convpx", 1, [55,75,330,295]], ["convpx", 1, [330,75,450,235]], ["convpx", 1, [470,190,815,295]], ["ignpx", 1, [[450,40,835,190],[325,235,440,330]]],
             ["conv", 2, list(range(999))], ["ignpx", 2, [[85,70,800,340]]])
add("m0262", ["conv", 0, []], ["conv", 1, []])
FLAGS = {"m0220": "v1 'potato' crowd (crowd 2) looks like kiwifruit next to pears; class unverifiable -> ignore region (suspected v1 mislabel)"}
add("m0350", ["keep", 0, "peppers stacked 3-4 deep; blocky bell vs pointed sweet pepper not verifiable per item"],
             ["conv", 1, list(range(999))], ["addpx", 1, [[165,124,280,239],[280,109,390,214],[385,139,470,224],[320,199,440,294],[450,214,495,309],[75,279,185,414],[230,214,340,349],[310,294,420,424],[420,304,495,414],[195,344,315,479],[125,394,215,494],[65,434,170,554],[165,474,300,579],[360,444,470,554],[430,499,495,574],[85,524,185,579]]])
add("m0428", ["conv", 0, list(range(999))], ["addpx", 0, [[190,158,450,248],[440,123,540,213],[495,158,615,318],[225,248,380,323],[360,263,500,393],[205,338,330,483],[290,323,470,498],[460,323,620,503],[610,233,680,363],[150,343,225,408]]],
             ["conv", 1, list(range(999))], ["addpx", 1, [[160,123,720,488]]])
FLAGS["m0428"] = "banana hand boundaries in the basket (crowd 0) and the held bunch (crowd 1, one or two hands) are ambiguous; boxes approximate"
FLAGS["m0350"] = "lemon boxes in the crate drawn by hand at review resolution (approximate)"
add("m0428", ["conv", 2, list(range(999))], ["addpx", 2, [[110,224,470,444],[205,419,420,574]]], ["conv", 3, list(range(999))], ["addpx", 3, [[140,124,540,564]]])
add("m0449", ["convpx", 0, [50,53,830,433], [335]], ["keep", 1, "tomatoes in a carton, cut off by the frame edge and shadowed"])
add("m0475", ["convpx", 0, [0,70,250,640]], ["convpx", 0, [0,170,620,640]], ["ignpx", 0, [[250,30,600,165]]],
             ["convpx", 1, [60,74,420,420], [63]], ["convpx", 1, [230,380,710,584], [63]], ["dupx", 0.7])
add("m0484", ["keep", 1, "small heaped tomatoes, green/red; green items not verifiable as tomato vs apple/guava per item"])
add("m0505", ["keep", 0, "carrots criss-crossed in a pile; individual boundaries ambiguous"])
add("m0549", ["keep", 0, "carrots criss-crossed in a crate; proposals fragment single roots"], ["keep", 1, "few crossed carrots at crate edge, partial"])
add("m0576", ["convpx", 0, [0,40,725,500]], ["convpx", 0, [0,500,480,660]], ["ignpx", 0, [[480,500,760,660]]],
             ["convpx", 1, [270,60,880,410]], ["convpx", 1, [60,190,270,410]], ["dupx", 0.6])
add("m0577", ["keep", 0, "dense carrot heap, roots overlap"],
             ["conv", 1, list(range(999))], ["addpx", 1, [[5,164,100,274],[40,169,180,274],[175,139,260,229],[255,144,365,264],[360,149,475,214],[335,204,505,294],[500,204,595,319],[5,254,150,424],[130,234,225,374],[220,249,320,404],[300,284,390,379],[390,294,505,404],[490,344,580,429],[5,344,200,454],[210,399,350,474],[110,434,250,559],[10,454,95,519]]],
             ["keep", 2, "large criss-crossed carrot pile, 3+ layers"])
add("m0592", ["convpx", 0, [120,78,770,368], [29,32,13,36]], ["convpx", 0, [120,368,450,548], [29,32,13,36]])
FLAGS["m0577"] = "crowd 1 carrots boxed by hand at review resolution (approximate)"
add("m0592", ["convpx", 2, [235,80,830,460], [81]], ["dupx", 0.6])
add("m0629", ["conv", 4, []], ["keep", 5, "green peppers out of focus; boundaries not verifiable"])
add("m0633", ["keep", 0, "carrot crate, roots criss-crossed 3+ deep"])
add("m0649", ["conv", 0, list(range(999))], ["addpx", 0, [[150,4,265,104],[215,24,365,144],[300,4,425,104],[360,74,490,189],[20,124,130,254],[105,164,240,274],[210,214,335,319],[285,154,400,254],[400,174,525,304],[45,244,160,359],[140,284,265,389],[255,324,375,404],[300,254,435,369],[410,309,540,374],[85,84,185,164],[185,109,290,214],[75,369,190,474],[665,59,750,209],[700,4,790,59],
                                         [640,312,740,419,3],[560,399,670,499,3],[670,424,765,524,3],[480,444,590,529,3]]],
             ["convpx", 1, [20,90,400,660]], ["convpx", 1, [400,290,530,660]], ["conv", 2, []], ["dupx", 0.5])
add("m0650", ["conv", 0, []], ["delsmallpx", 0, 30], ["dupx", 0.6])
FLAGS["m0649"] = "netted apples boxed by hand at review resolution; mandarin boxes from OWLv2 proposals"
FLAGS["m0650"] = "oranges seen through basket slats (<50% visible) left unboxed but NOT ignored -> a detection there counts as false; flagged as ambiguous"
# rule: proposal-based conversions keep the v1 region as a residual crowd (members not boxed stay ignored); hand-enumerated conversions remove it
for I, ks in {"m0650": [0], "m0262": [0, 1], "m0449": [0], "m0475": [0, 1], "m0649": [1, 2], "m0629": [4], "m0024": [3], "m0576": [0, 1], "m0592": [0, 2], "m0220": [0, 1]}.items():
    add(I, *[["recrowd", k] for k in ks])
add("m0653", ["convpx", 0, [30,70,560,575]], ["convpx", 0, [560,230,880,575]], ["recrowd", 0],
             ["conv", 1, list(range(999))], ["addpx", 1, [[90,114,210,239],[160,124,280,274],[265,134,320,214],[315,94,460,219],[475,134,600,214],[325,204,485,364],[300,189,365,284],[410,314,560,394],[530,239,685,384],[665,289,790,364],[305,329,360,364]]],
             ["conv", 2, []], ["recrowd", 2],
             ["conv", 3, list(range(999))], ["addpx", 3, [[95,223,305,388]]], ["crowdpx", 3, [[270,0,800,100]]], ["dupx", 0.6])
add("m0663", ["keep", 0, "plantain hands piled 2-4 deep; hand boundaries not separable"], ["keep", 1, "2-3 pale green items behind a post; cucumber vs gourd not verifiable"])
add("m0676", ["keep", 0, "carrots criss-crossed in crates"])
add("m0684", ["convpx", 0, [320,40,880,470]], ["convpx", 0, [85,220,320,470]], ["recrowd", 0], ["dupx", 0.6])
add("m0684", ["conv", 1, list(range(999))], ["ignpx", 1, [[140,130,740,510]]])
FLAGS["m0684"] = "v1 'potato' crowd (crowd 1) looks like kiwifruit (fuzzy brown ovals next to limes); class unverifiable at this resolution -> ignore region (suspected v1 mislabel)"
add("m0687", ["conv", 0, []], ["recrowd", 0], ["dupx", 0.6])
add("m0707", ["conv", 0, [51, 67]], ["recrowd", 0], ["conv", 1, []], ["recrowd", 1])
add("m0707", ["conv", 2, [1]], ["recrowd", 2], ["conv", 3, [26]], ["recrowd", 3], ["conv", 4, [19]], ["recrowd", 4], ["dupx", 0.6])
add("m0719", ["keep", 0, "banana hands overlapping on a wheelbarrow; proposals are finger fragments"])
NEW = {}
NEW["m0003"] = ["tomato basin + carrot bunch crowd (items ~15 px); far mixed row ignored; pumpkins non-target", [["crowd",0.44,0.78,0.78,1.0,7],["crowd",0.55,0.6,0.72,0.82,10],["ign",0.56,0.44,0.96,0.6]]]
NEW["m0004"] = ["tomato basins crowd; far stalls ignored; leafy greens non-target", [["crowd",0.52,0.62,0.71,0.87,7],["crowd",0.32,0.87,0.52,1.0,7],["ign",0.05,0.46,0.21,0.54],["ign",0.6,0.41,0.79,0.53]]]
NEW["m0047"] = ["red potato heap + small baskets crowd; onions, garlic, ginger non-target", [["crowd",0.0,0.6,0.5,1.0,8],["crowd",0.0,0.24,0.12,0.33,8]]]
NEW["m0058"] = ["carrot heap and banana hands crowd; PRINTED banana on carton is a negative; far stalls ignored", [["crowd",0.2,0.4,0.41,0.61,10],["crowd",0.39,0.55,0.62,0.87,0],["ign",0.1,0.15,0.42,0.28],["ign",0.5,0.2,0.62,0.28]]]
NEW["m0188"] = ["Kabul stall: orange trays, apple crate, hanging bananas crowd (items ~15 px)", [["crowd",0.33,0.5,1.0,0.88,3],["crowd",0.2,0.42,0.33,0.56,3],["crowd",0.22,0.72,0.42,0.93,1],["crowd",0.48,0.12,0.6,0.45,0]]]
NEW["m0426"] = ["green round fruit with leaves (guava vs green apple not verifiable) ignored; cut fruit in hand ignored", [["ign",0.3,0.05,1.0,0.5],["ign",0.54,0.58,0.63,0.71]]]
NEW["m0531"] = ["Ballarat apples in basket boxed by hand; cut-off red apples at bottom crowd", [["add",*b,1] for b in [[0,0.29,0.22,0.55],[0.145,0.19,0.30,0.36],[0.27,0.10,0.41,0.27],[0.225,0.25,0.36,0.46],[0.34,0.23,0.53,0.49],[0.50,0.23,0.58,0.35],[0.57,0.25,0.68,0.36],[0.73,0.17,0.87,0.34],[0.64,0.30,0.75,0.43],[0.57,0.35,0.65,0.45],[0.25,0.45,0.44,0.58],[0.44,0.46,0.62,0.58],[0.72,0.39,0.93,0.58],[0.62,0.41,0.73,0.57],[0.20,0.45,0.26,0.56]]] + [["crowd",0,0.91,1,1,1]], True]
NEW["m0558"] = ["apple crates: OWLv2 apple boxes kept, crates residual crowd; far crates crowd; sign/crate fragments deleted", [["del",0,0,1,0.18],["del",0.3,0.78,1,1],["rel",0,0,1,1,-1,1],["crowd",0.08,0.05,0.45,0.18,1],["crowdk",0,0.18,1,0.78,1]]]
NEW["m0582"] = ["orange basin crowd; pomelos (citrus vs non-target pomelo ambiguous) and fruit bowls ignored", [["crowd",0.22,0.25,0.76,0.56,3],["ign",0.06,0.47,0.4,0.66],["ign",0.42,0.14,0.8,0.31]]]
NEW["m0590"] = ["hanging banana hands crowd; lower fruit display ignored; printed/red lanterns negatives", [["crowd",0.34,0.52,1.0,0.88,0],["ign",0,0.82,1,1]]]
NEW["m0641"] = ["juice stand: oranges in crate and behind glass counter crowd", [["crowd",0,0.37,0.23,0.51,3],["crowd",0,0.69,0.92,1.0,3]]]
NEW["m0671"] = ["indoor market: red tomato boxes crowd; green produce (green tomato vs pepper) and far crates ignored", [["crowd",0.0,0.52,0.45,0.97,7],["ign",0.42,0.25,1.0,0.86],["ign",0,0.25,0.42,0.52]]]
NEW["m0680"] = ["Biocoop: mandarins in basket boxed by hand + residual crowd; banana hands crowd; brown ovals top-right (mango vs other) ignored; printed signs negatives",
    [["add",*b,3] for b in [[0.40,0.51,0.475,0.60],[0.335,0.55,0.40,0.66],[0.45,0.59,0.52,0.69],[0.28,0.65,0.36,0.78],[0.34,0.63,0.415,0.75],[0.415,0.63,0.49,0.73],[0.52,0.69,0.60,0.79],[0.34,0.75,0.43,0.875],[0.43,0.77,0.505,0.88],[0.49,0.78,0.57,0.875],[0.39,0.69,0.465,0.79]]]
    + [["crowdk",0.27,0.5,0.62,0.92,3],["crowd",0,0.37,1.0,1.0,0],["ign",0.7,0.3,1.0,0.62]], True]
NEW["m0693"] = ["apple fair: small apples in crate crowd; side baskets ignored; printed 'Manzanas' card negative", [["crowd",0.47,0.49,0.96,0.66,1],["ign",0.93,0.38,1.0,0.62],["ign",0.5,0.37,0.63,0.46]]]
NEW["m0699"] = ["Ghana market: bell peppers, carrots, cucumbers, bananas crowd; papaya/mango mix and far stalls ignored; papaya, watermelon, cabbage, garden eggs non-target",
    [["crowd",0.53,0.48,0.74,0.61,11],["crowd",0.76,0.53,0.98,0.66,10],["crowd",0.02,0.87,0.28,1.0,9],["crowd",0.37,0.72,0.52,0.84,9],["crowd",0.62,0.84,0.76,1.0,0],["ign",0.25,0.0,0.62,0.31],["ign",0.5,0.71,0.76,0.86],["ign",0.22,0.67,0.33,0.81]]]
NEW["m0702"] = ["small tomatoes on sack crowd; basket of small items ignored; eggplants, onions, cabbage non-target", [["crowd",0.18,0.63,0.66,1.0,7],["ign",0.47,0.24,0.73,0.37],["ign",0.48,0.38,0.62,0.48],["ign",0.08,0.5,0.2,0.6]]]
NEW["m0726"] = ["roadside: limes in basket crowd lemon_lime; small brown items and pink bag (corn?) ignored; pumpkins and ash gourds are non-target hard negatives", [["crowd",0.13,0.63,0.31,0.78,6],["ign",0.27,0.38,0.37,0.51],["ign",0,0.62,0.13,0.79]]]
# Zoom QA of proposal-based conversions (ls/z0.jpg, ls/z1.jpg, ls/m0592.jpg): OWLv2 region boxes in dense piles are often misaligned,
# fragmented or merged (m0684, m0592, m0649:1-2, m0576, m0653:0/2 clearly; m0449 marginal). Rule: a proposal-based conversion is accepted
# only if the zoom check shows tight single-item boxes (accepted: m0262 limes, m0707 tomatoes, m0687 tomatoes); every other
# proposal-based conversion (incl. the unchecked ones) is reverted to the v1 crowd region.
REVERT = {("m0684",0),("m0592",0),("m0592",2),("m0649",1),("m0649",2),("m0576",0),("m0576",1),("m0653",0),("m0653",2),("m0449",0),
          ("m0220",0),("m0220",1),("m0475",0),("m0475",1),("m0629",4),("m0024",3),("m0650",0)}
NEW["m0558"][1] = [["del",0,0,1,1]] + [o for o in NEW["m0558"][1] if o[0] != "del"]
# Adjudication after the different-crop second pass (pass 2 found pass-1 omissions; fixed before v2 freeze, before any v2 evaluation)
add("m0629", ["crowd", 0.34, 0.55, 0.45, 0.67, 9])   # cucumbers in a basket were unlabelled (pass-1 omission)
add("m0582", ["crowd", 0.22, 0.40, 0.30, 0.50, 1])   # small apples at the basin edge were unlabelled (pass-1 omission)
