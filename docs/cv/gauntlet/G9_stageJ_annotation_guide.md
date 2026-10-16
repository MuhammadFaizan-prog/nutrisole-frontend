# NutriSole photo labelling guide (G9 Stage J)

**Who this is for:** the two people labelling photos (Faizi and one FYP teammate). You do not need to know anything about machine
learning. You are telling us, honestly, what the main thing in each photo is. Your answers become the "ground truth" the app is
tested against, so careful and honest beats fast.

**Time:** about 3-5 seconds per photo. The pilot (265 photos) takes about 20-30 minutes; the training batch (458 photos) about 40 minutes.
Take a break whenever you like: your work saves itself.

---

## 1. The one question

> **What is the MAIN item in the centre of the photo?**

- "Main item" = the thing in the middle of the photo, the one a phone user would tap. If there are several fruits, judge the one in the
  centre (and add the tag **M**, many items).
- Choose **one** answer with keys **1-9**. Go with your first honest impression. Do not search the internet and do not ask the other
  labeller.
- **9 (uncertain) is a good answer.** A wrong confident label hurts us more than an honest "uncertain".

## 2. The nine answers

| Key | Answer | Choose it when | Do NOT choose it when |
|---|---|---|---|
| **1** | `apple` | A real apple of any colour (red, green, yellow, mixed), with or without spots, bruises or a sticker. | It is an apple pie, juice, an apple-shaped toy, or apple blossom/tree with no clear fruit (→ 7 or 9). |
| **2** | `banana` | A real banana or a bunch of bananas, from green to brown-spotted. | Banana bread, banana leaf only. Plantain: only if you are sure it is a banana-type fruit; otherwise 9. |
| **3** | `citrus_orange` | **Orange-type citrus:** orange, **kinnow**, **malta**, mandarin, tangerine, clementine, satsuma, blood orange. Peeled segments still count (add tag **C**). | **Lemon or lime** (yellow or green, smaller, pointed ends) → **6**. **Grapefruit or pomelo** (much bigger) → **6**. Orange juice or slices in a drink → 9. |
| **4** | `tomato` | A real tomato: red, orange, yellow or green; big, plum or cherry tomato. | Tomato sauce/ketchup, a tomato plant with no clear fruit (→ 9). |
| **5** | `carrot` | A real carrot root: orange (also purple/yellow carrots). With or without leaves, whole or a bunch. | Only carrot leaves visible; grated carrot in a salad (→ 9 or 6 with a note). |
| **6** | `other_produce` | A **real** fruit or vegetable that is none of 1-5: lemon, lime, mango, guava, pomegranate, potato, onion, cucumber, **capsicum (bell pepper)**, **chili**, peach, plum, persimmon, kiwi, radish, beetroot, sweet potato, papaya, grapes, etc. Pick its name from the list if you know it. | It is a picture/toy (→ 7). |
| **7** | `printed_or_screen` | Not real produce: a **photo of a photo**, poster, magazine, painting, drawing, screen, sign, **plastic/wax/toy fruit**, map. | It is real fruit that just looks shiny (→ 1-6). |
| **8** | `occluded` | Real produce, but **less than about half** of the main item is visible: covered by a hand, cloth, another fruit, a non-see-through bag, or cut off by the photo edge. Optionally say what it is underneath. | You can still see most (about half or more) of it → choose the fruit (1-6) and add tags (**B** if it is in a clear bag, **M** if in a pile). |
| **9** | `uncertain` | You cannot tell what it is; the photo is too dark/blurry/small; there is no clear main item; or two answers seem equally right. Write a short note if you can. | - |

### Class rules in one line each (how they map to the app's 13 classes)
- `citrus_orange` = the app's **citrus** class (orange, mandarin, clementine, tangelo, kinnow, malta). **Lemon and lime are a separate app
  class (`lemon_lime`)**, so they are labelled `other_produce` + name `lemon_or_lime`. Grapefruit, pomelo and kumquat are kept out of the
  citrus class entirely (`other_produce` + name).
- **Capsicum** in the app means a **whole bell pepper** (green, red, yellow). **Chilies are not capsicum.** Both are `other_produce`;
  pick `capsicum_bell_pepper` or `chili` from the name list so the two stay apart.
- The other app classes (mango, guava, pomegranate, potato, cucumber, capsicum, lemon/lime) are labelled `other_produce` with their name.
  That keeps all 13 app classes recoverable from your labels while you only make 9 choices.

## 3. Tags (optional extras, press again to remove)

| Key | Tag | Meaning |
|---|---|---|
| **C** | cut / peeled / sliced | The main item is not whole: cut in half, sliced, peeled, segments. Still choose what it is (1-6). |
| **B** | in a bag / net / packet | The main item is inside packaging. If you can see it clearly through the bag, choose the fruit (1-6) + **B**. If you mostly cannot see it, choose **8**. |
| **M** | many items / pile | Several items, a bunch, a bowl, a market stall. Judge the centre item. |
| **X** | rotten / damaged | Clearly rotten, mouldy, crushed or badly bruised. Still choose what it is. |
| **N** | note | Type anything useful ("centre one is a lime", "screen photo", "two fruits overlap"). `Esc` leaves the note box. |

## 4. Tricky cases (decided in advance, so both labellers do the same)

| Situation | Answer |
|---|---|
| A bowl of mixed fruit, apple in the centre | `apple` + **M** |
| A market stall of oranges, no single centre item | `citrus_orange` + **M** (if they are all the same kind); mixed fruits with no clear centre → `uncertain` |
| An orange cut in half | `citrus_orange` + **C** |
| A green "orange" that might be a lime | If clearly round with thick bumpy skin, orange-sized → `citrus_orange`; small and smooth → `other_produce` / `lemon_or_lime`; can't tell → `uncertain` |
| Kinnow / malta / mandarin | `citrus_orange` |
| Lemon, lime, sweet lime (mosambi) | `other_produce` with `lemon_or_lime` (note "mosambi" for sweet lime) |
| Grapefruit, pomelo | `other_produce` with `grapefruit_or_pomelo` |
| Green bell pepper vs green chili | bell pepper (blocky, thick) → `other_produce` / `capsicum_bell_pepper`; chili (thin, pointed) → `other_produce` / `chili` |
| Cherry tomatoes in a punnet you can see through | `tomato` + **B** + **M** |
| Apples in a white bag, only tops visible (less than half) | `occluded` (say `apple` underneath if you can) + **B** |
| A hand holding a banana, most of the banana visible | `banana` (hands are fine if the fruit is mostly visible) |
| Fruit on a phone or laptop screen, a fridge magnet, a poster | `printed_or_screen` |
| Plastic / wax / toy fruit | `printed_or_screen` |
| Fruit drawn or painted, an old botanical print | `printed_or_screen` |
| A fruit tree / orchard where the fruit is tiny in the photo | `uncertain` (note "too small") unless one fruit clearly fills the centre |
| Juice, jam, pie, salad, cooked dish | `uncertain` with a note (it is not a whole raw item) |
| Black and white photo of a fruit | label the fruit if you are sure, otherwise `uncertain` |
| A photo with no fruit or vegetable at all | `uncertain` with note "no produce" |

## 5. How to work

1. Open the `.html` file from your zip (double-click). Type your name. Press **?** to see the short guide any time.
2. Label each photo: number key, then tags if needed. The tool jumps to the next photo by itself (except after 6 and 8, so you can pick a
   name; press → to move on).
3. Use **U** to jump to the next photo you have not labelled yet. Use ← to go back and change an answer.
4. Press **Export CSV** when you finish, or at the end of each session, and send the file. Exporting twice is fine; the newest file wins.
5. **Do not talk about the photos with the other labeller until both of you have exported.** Disagreements are expected and useful; a
   third person (the adjudicator) settles them afterwards.
6. If the tool does not open, use the fallback CSV and the contact sheets (`fallback/` folder): look up each id on the sheet and write one
   of the nine answers in the `label` column, exactly as spelled above.

## 6. What happens with your labels (for the curious)

- The two exported files are compared automatically. Photos where you agree become verified; photos where you disagree, or where either
  of you chose `uncertain`, go to an adjudicator who decides.
- Agreement is measured with Cohen's kappa (a score where 1.0 means perfect agreement and 0 means agreement no better than chance).
  If agreement is too low (below 0.85 for the fruit name), the definitions get clarified and the disagreeing photos are relabelled.
- The **pilot** photos are kept aside to **test** the app; the **training** photos are used later to teach the model. They come from
  different photographers and websites so the test stays fair.
