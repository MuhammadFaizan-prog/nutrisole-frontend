# MT (market-train) agent decisions: region-level correction of OWLv2 proposals (class verification, deletion of non-target regions,
# greying of unverifiable regions); item-level box tightness is NOT verified except for hand-boxed images ("scratch").
E = {}
def ok(i, note, *ops, thr=0.30): E[i] = dict(note=note, thr=thr, ops=list(ops))
def neg(i, note): E[i] = dict(neg=True, note=note)
def rej(i, note): E[i] = dict(status="rejected", note=note)
ok("t000", "orange/grapefruit crate mixed and dense -> greyed; rest of stall has no verifiable targets", ["grey",0.17,0.44,1,0.69], ["grey",0,0.41,0.11,0.57], ["del",0,0,1,1])
ok("t001", "HK fruit stall: orange pile + top shelf citrus, red apples, yellow mangoes; netted pears, grapes, watermelon, decorations deleted",
   ["del",0,0,1,0.47], ["del",0.75,0.45,1,0.72], ["del",0.4,0.8,0.78,1], ["del",0.72,0.72,0.9,0.88],
   ["rel",0,0.6,0.45,1,-1,3], ["rel",0.15,0.47,0.47,0.62,-1,3], ["rel",0.42,0.62,0.6,0.8,-1,1], ["rel",0.66,0.55,0.82,0.72,-1,2])
ok("t002", "Southall orange/clementine stall, dense; all citrus; pomegranates/apples at right edge deleted", ["del",0.9,0.5,1,0.9], ["rel",0,0.2,0.92,0.7,-1,3], ["del",0,0.7,1,1])
ok("t003", "mandarin close-up boxed by hand (scratch)", ["del",0,0,1,1], *[["add",*b,3] for b in [[0.17,0.07,0.44,0.47],[0.43,0.18,0.67,0.48],[0.66,0.08,0.92,0.42],[0.0,0.28,0.2,0.63],[0.27,0.43,0.6,0.88],[0.55,0.38,0.79,0.75],[0.71,0.32,1.0,0.72],[0.5,0.0,0.73,0.2]]], ["grey",0,0,0.16,0.27], ["grey",0.86,0,1,0.2])
ok("t004", "mandarin heap: all citrus (proposal boxes noisy)", ["all",3])
ok("t005", "Bhutan mandarin heaps and baskets: all citrus", ["all",3])
ok("t006", "mandarin close-up: all citrus (proposal boxes noisy)", ["all",3])
ok("t007", "kinnow display: all citrus", ["all",3])
ok("t008", "Junar citrus on tree: all citrus", ["all",3])
ok("t009", "lemons + limes = lemon_lime; pomelos (citrus/non-target ambiguous) greyed", ["grey",0.6,0.05,1,1], ["all",6])
ok("t010", "mosambi (sweet lime = citrus per class rule)", ["all",3])
ok("t011", "Cosmic Crisp apples bin; PRINTED apples on cartons deleted (negatives); upper produce shelves deleted", ["del",0,0.68,1,1], ["del",0,0,1,0.3], ["all",1])
rej("t012", "supermarket island: apples, mandarins, kiwis mixed and dense; classes not separable by region")
rej("t013", "Arequipa stall: papaya, pineapple, mango, banana, tree tomato mixed; not verifiable by region")
rej("t014", "Bangalore stall: apples, sweet lime, custard apple, grapes, guava mixed; not verifiable by region")
neg("t015", "ARTIFICIAL (plastic) produce display at the Big E: fake lettuce, peppers, cucumbers, apples are NOT targets -> hard negative")
ok("t016", "Bangalore mango stall: mangoes; red apples top and left; far pineapples deleted", ["del",0.66,0.2,1,0.4], ["rel",0.08,0.45,0.66,1.0,-1,2], ["rel",0,0.43,0.13,0.72,-1,1], ["rel",0.29,0.36,0.52,0.47,-1,1])
ok("t017", "banana stall: all banana (hands, proposal boxes noisy); glare corner deleted", ["del",0.7,0,1,0.45], ["all",0])
ok("t018", "Yabelo: hanging banana bunches boxed (bunch-level proposals kept); far small fragments deleted", ["del",0.5,0.4,1,0.8], ["del",0.5,0.25,0.75,0.4], ["all",0])
ok("t019", "Kigali stall: mangoes in carton kept; banana hands (finger-level proposals) and green citrus/mango basket greyed; avocados, watermelons, PRINTED 'CITRUS' carton = negatives",
   ["grey",0.08,0.17,0.97,0.47], ["grey",0.42,0.4,0.92,0.58], ["del",0,0,1,0.84], ["rel",0.35,0.84,0.7,1,-1,2])
rej("t020", "plantain hands: proposals are finger-level (class rule = one box per hand); hand boundaries not drawn within budget")
ok("t021", "Carrara: hanging banana bunches boxed by hand; table piles greyed; PRINTED banana posters = negatives", ["del",0,0,1,1],
   ["add",0.3,0.22,0.46,0.5,0], ["add",0.6,0.18,0.78,0.46,0], ["add",0.07,0.27,0.17,0.4,0], ["add",0.0,0.29,0.07,0.4,0], ["grey",0.18,0.68,0.42,0.8], ["grey",0.44,0.71,0.79,0.93])
rej("t022", "banana bunches on stalks, overlapping; finger-level proposals")
rej("t023", "strawberry banana hands in bowls; finger-level proposals")
ok("t024", "banana hands in a carton boxed by hand (approximate hand extents); top and bottom rows greyed", ["del",0,0,1,1],
   ["add",0.0,0.5,0.3,0.8,0], ["add",0.2,0.25,0.5,0.8,0], ["add",0.4,0.28,0.72,0.78,0], ["add",0.62,0.28,0.93,0.75,0], ["grey",0.15,0.07,0.82,0.24], ["grey",0,0.85,0.72,1])
ok("t025", "Badagry: plantain hand + 2 yellow banana hands boxed by hand", ["del",0,0,1,1], ["add",0.27,0.35,0.49,0.73,0], ["add",0.47,0.38,0.68,0.73,0], ["add",0.66,0.4,0.84,0.66,0])
rej("t026", "Jaipur cart: small mixed bananas/guavas/apples; not verifiable by region")
ok("t027", "Iloilo shelf: tomatoes (all tomato); cabbages, napa, chayote non-target", ["del",0.93,0,1,1], ["rel",0.1,0.55,0.95,1,-1,7], ["del",0,0,1,0.55])
ok("t028", "Borough Market heirloom tomatoes (red/orange/yellow, partly blurred): all tomato", ["all",7])
ok("t029", "HK tomato crates: all tomato; chayote/gourds at top deleted", ["del",0.35,0,0.9,0.13], ["all",7])
ok("t030", "tomato baskets (all tomato); scotch-bonnet chilies at bottom and left items deleted (chilies are negatives)", ["del",0,0.7,0.65,1], ["del",0,0.55,0.2,0.8], ["rel",0,0.15,1,0.72,-1,7], ["del",0,0,1,0.15])
ok("t031", "tomato heap close-up: all tomato; red chilies at right edge deleted", ["del",0.9,0.45,1,1], ["all",7])
ok("t032", "greenhouse tomatoes in carton: all tomato (printed carton text)", ["all",7])
ok("t033", "HK stall: potatoes (left) and tomatoes (right); carrots top-right; avocados, ginger, signs deleted",
   ["del",0,0,0.6,0.3], ["del",0.5,0.2,0.8,0.42], ["del",0,0.3,0.2,0.5], ["rel",0,0.42,0.47,1,-1,8], ["rel",0.45,0.42,1,1,-1,7], ["rel",0.6,0.1,0.75,0.25,-1,10])
ok("t034", "HK veg stall: tomatoes kept; eggplant, cassava, bamboo shoot, corn, radish, garlic, beans, avocado deleted", ["rel",0.6,0.15,1,0.45,-1,7], ["del",0,0,0.6,1], ["del",0.6,0.45,1,1], ["del",0.6,0,1,0.15])
rej("t035", "wide market: tiny tomato heaps mixed with onions; not separable")
ok("t036", "Ifaty stall: row of small tomatoes (all tomato); sugar cane, beans non-target", ["rel",0,0.55,0.62,0.8,-1,7], ["del",0,0,1,0.55], ["del",0.62,0,1,1], ["del",0,0.8,1,1])
ok("t037", "German veg crates: carrots, baby potatoes, cucumbers (bottom); PRINTED carrots on paper bags, courgettes, radish, garlic, eggplant, chard deleted; mixed fruit right greyed",
   ["del",0.38,0.25,0.68,0.95], ["del",0.1,0.25,0.38,0.68], ["del",0,0,0.37,0.35], ["del",0,0.58,0.2,0.76], ["grey",0.78,0.12,1,0.58],
   ["rel",0.5,0,0.8,0.25,-1,10], ["rel",0.37,0,0.52,0.17,-1,8], ["rel",0,0.75,0.38,1,-1,9])
ok("t038", "carrot pile close-up: all carrot (proposal boxes noisy)", ["all",10])
ok("t039", "Kaduna carrots in baskets: all carrot (noisy)", ["all",10])
ok("t040", "carrots in crate: all carrot; PRINTED carrot packaging and red cabbage deleted", ["del",0.68,0.72,1,1], ["del",0,0,0.25,1], ["all",10])
ok("t041", "carrot close-up + green bell peppers top-left (capsicum); red chilies deleted", ["del",0,0,0.22,0.06], ["all",10], ["rel",0,0,0.35,0.32,-1,11])
ok("t042", "farmers market: carrots kept; delicata squash and kale deleted (non-target)", ["del",0.5,0.4,1,1], ["del",0.42,0.4,0.6,0.56], ["rel",0,0.1,0.45,0.65,-1,10], ["del",0.45,0,1,0.4])
ok("t043", "Kaduna: carrots; green bell peppers top band (capsicum); top-left cucumbers greyed", ["all",10], ["rel",0.12,0,0.45,0.14,-1,11], ["grey",0,0,0.12,0.3])
ok("t044", "Kaduna: green bell peppers + cucumbers + carrots (bottom); OWLv2 classes kept where cucumber/capsicum, other labels in the upper area -> capsicum (noisy)",
   ["rel",0,0,1,0.72,10,11], ["rel",0,0,1,0.72,6,11], ["rel",0,0,1,0.72,7,11], ["rel",0,0,1,0.72,1,11], ["rel",0,0.72,0.55,1,-1,10], ["del",0.55,0.72,1,1])
ok("t045", "red bell peppers close-up: all capsicum; pale pointed chili at left deleted", ["del",0,0,0.2,0.32], ["all",11])
ok("t046", "Lisbon bell peppers (red/orange/yellow/green): all capsicum", ["all",11])
ok("t047", "orange bell peppers in basket: all capsicum", ["all",11])
ok("t048", "Kaduna cucumbers; carrots in the top band; cabbage at left deleted", ["del",0,0,0.1,0.5], ["all",9], ["rel",0.3,0,0.92,0.17,-1,10])
ok("t049", "Onitsha cucumbers; CUT carrot sticks (not targets) and bottles deleted", ["del",0,0,0.27,0.18], ["del",0.72,0,1,0.55], ["all",9])
ok("t050", "HK cucumbers in basket: all cucumber", ["all",9])
ok("t051", "Ashdod pomegranates: all pomegranate; OPENED pomegranates greyed (cut = not target); background stall deleted", ["del",0.86,0,1,1], ["grey",0.3,0.33,0.46,0.5], ["grey",0.66,0.22,0.87,0.43], ["all",5])
ok("t052", "Serbian market pomegranates in carton: all pomegranate; background crates deleted", ["del",0.9,0,1,1], ["del",0,0,1,0.18], ["all",5])
ok("t053", "Kolkata pomegranates close-up: all pomegranate; bokeh edge items deleted", ["del",0.9,0,1,1], ["all",5])
ok("t054", "Pune guava cart: all guava (incl. one held by a child)", ["all",4])
ok("t055", "Alagar Koil guava vendors (wide, small items): all guava", ["all",4])
ok("t056", "Puno: grey potatoes (front) = potato; pink tubers (oca/ulluco vs red potato unverifiable) greyed; oca sack, chuño deleted",
   ["del",0.5,0.28,1,0.86], ["grey",0,0.43,0.5,0.62], ["rel",0,0.55,0.5,1,-1,8], ["del",0,0,1,0.43])
ok("t057", "Indonesian gedong gincu mangoes (orange-red and green): all mango", ["all",2])
ok("t058", "Iloilo: carrots kept; small green citrus in crates (calamansi vs lime) and left edge greyed; gourds, eggplant, radish deleted",
   ["grey",0.12,0.5,0.75,1], ["grey",0,0,0.1,0.45], ["rel",0,0.2,0.32,0.5,-1,10], ["del",0.32,0,1,0.5], ["del",0,0,0.32,0.2])
ok("t059", "Iloilo: carrots (left) kept; onions, ginger, cauliflower, cabbage, chayote, bagged items deleted", ["rel",0.05,0.38,0.32,0.82,-1,10], ["del",0.32,0,1,1], ["del",0,0,0.32,0.38], ["del",0,0.82,1,1])
ok("t060", "Iloilo: carrot/potato baskets (OWLv2 carrot/potato classes kept), yellow lemons, cherry tomatoes; garlic, broccoli, lettuce, bagged items deleted",
   ["rel",0.3,0.42,0.55,0.7,-1,6], ["rel",0.5,0.8,0.66,1,-1,7], ["del",0,0,0.5,0.42], ["del",0,0.7,0.5,1], ["del",0.66,0.55,1,1], ["del",0.88,0,1,0.55], ["del",0.5,0,1,0.24])
ok("t061", "Goa: tomatoes, potatoes, cucumbers kept; onions, beans, bitter gourd, greens deleted",
   ["rel",0,0.53,0.45,0.77,-1,7], ["rel",0.62,0.72,1,1,-1,8], ["rel",0,0.84,0.2,1,-1,9], ["del",0,0,1,0.53], ["del",0.45,0.53,1,0.72], ["del",0.2,0.77,0.62,1])
ok("t062", "Jaipur: limes in two baskets (lemon_lime), tomatoes right; melons, okra, beans, green chilies, cauliflower deleted",
   ["rel",0.22,0.55,0.62,0.76,-1,6], ["rel",0.68,0.62,1,0.9,-1,6], ["rel",0.85,0.3,1,0.56,-1,7], ["del",0,0,1,0.3], ["del",0,0.3,0.85,0.55], ["del",0,0.55,0.22,1], ["del",0.22,0.76,0.68,1], ["del",0.62,0.55,0.68,0.76], ["del",0.68,0.9,1,1], ["del",0.62,0.55,1,0.62])
ok("t063", "Adjamé 'citrons' (lemons) in clear bags: all lemon_lime; brown items at right deleted", ["del",0.8,0.7,1,1], ["all",6])
ok("t064", "bell peppers yellow/red/orange: all capsicum", ["all",11])
ok("t065", "Riga cucumbers + tomatoes in the top band / right: cucumber, tomato", ["all",9], ["rel",0,0,1,0.16,-1,7], ["rel",0.68,0.08,1,0.36,-1,7])
for i, n in [("t066","feijoa (pineapple guava) - unsupported produce"),("t067","kakis (persimmons) in crates + chalk sign"),("t069","persimmons on cloth + printed sign"),
             ("t070","single persimmon"),("t072","pitaya (dragon fruit) heap"),("t074","plastic bags with PRINTED fruit"),("t075","clothing market street"),
             ("t076","fabric/clothing stalls with printed signs"),("t077","woven bags and coconut crafts"),("t078","weighing scale, dry fruit bins"),("t079","stacked market crates"),
             ("t080","PRINTED fruit illustration (Millot plate)"),("t081","slot machine reels (printed symbols)"),("t082","slot machine reels with PRINTED cherries"),
             ("t083","kinnow juice bottles (no whole fruit)"),("t085","cooked food platter"),("t086","round candies (gobstoppers)"),("t087","Skittles candies")]:
    neg(i, n)
ok("t068", "persimmons (negative); mixed fruit at the top edge greyed", ["del",0,0,1,1], ["grey",0,0,1,0.2])
ok("t071", "dragon fruit (negative); apples/yellow fruit at left and bottom-right edges greyed", ["del",0,0,1,1], ["grey",0,0,0.07,0.6], ["grey",0.84,0.6,1,1])
ok("t073", "Ljubljana berries stall (negative); top-row stone fruit/apples greyed", ["del",0,0,1,1], ["grey",0,0,1,0.32])
ok("t084", "red chili heap (negative) + one whole cucumber boxed; pale item at right greyed", ["del",0,0,1,1], ["add",0.78,0.13,0.875,0.53,9], ["grey",0.88,0.12,1,0.58])
