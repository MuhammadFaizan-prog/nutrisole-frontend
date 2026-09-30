# Synthetic local data schema

No database. DemoState version 1 includes profile, connection/image-retention preferences, consumed meals, drafts, accepted day/meal keys, substitutes, and feedback. The current meal type represents Apple implicitly and includes id, submission key, edible grams, calories, and created timestamp. Duplicate submission keys cannot increase totals twice. Drafts do not contribute to consumed totals; converting a draft removes its matching saved record.

Storage key `nutrisole.demo.v1` contains synthetic data only. Version and shape checks reject corrupt storage. Reset clears this app's synthetic namespace only. On web use localStorage; on native use AsyncStorage. Screen history and transient sheet state remain in memory. Original Home/Plan initial meal summaries intentionally describe separate fixtures.
