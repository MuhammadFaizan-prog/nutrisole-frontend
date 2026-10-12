// v1 class order. MUST equal ml/data/class_map.csv nutrisole_id order and the `names`
// in ml/configs/det_v1.yaml (asserted in native/tests/cvContracts.test.ts).
// Never ship a model whose class order is unknown (rule 8.12).
export const V1_CLASSES = [
  { id: 0, classId: 'banana', en: 'Banana', ur: 'Kela' },
  { id: 1, classId: 'apple', en: 'Apple', ur: 'Saib' },
  { id: 2, classId: 'mango', en: 'Mango', ur: 'Aam' },
  { id: 3, classId: 'citrus', en: 'Citrus (orange / kinnow / mosambi)', ur: 'Malta / Kinnow' },
  { id: 4, classId: 'guava', en: 'Guava', ur: 'Amrood' },
  { id: 5, classId: 'pomegranate', en: 'Pomegranate', ur: 'Anaar' },
  { id: 6, classId: 'lemon_lime', en: 'Lemon / lime', ur: 'Leemu' },
  { id: 7, classId: 'tomato', en: 'Tomato', ur: 'Tamatar' },
  { id: 8, classId: 'potato', en: 'Potato', ur: 'Aloo' },
  { id: 9, classId: 'cucumber', en: 'Cucumber', ur: 'Kheera' },
  { id: 10, classId: 'carrot', en: 'Carrot', ur: 'Gajar' },
  { id: 11, classId: 'capsicum', en: 'Capsicum', ur: 'Shimla mirch' },
] as const;
export const QUALITY_LEVELS_2 = ['fresh', 'rotten'] as const;
