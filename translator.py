import os
import re
import json
import pandas as pd
from pathlib import Path
from openai import OpenAI

# Paths
LOCALIZATION_DIR = Path("../Excel/Localization/english")
LORE_BIBLE_PATH = Path("lore_bible.json")

# Regex for finding game variables, tags, and formatting
PLACEHOLDER_PATTERN = re.compile(r'(\{[0-9]+\}|\[\$tagrole:[^\]]+\$\]|\[\[[a-z]+:[^\]]+\]\])')

BATCH_SIZE = 200

class LoreBible:
    def __init__(self):
        self.data = {
            "characters": set(),
            "factions": set(),
            "locations": set(),
            "mechanics": set(),
            "general_glossary": {}
        }
        self.load()

    def load(self):
        if LORE_BIBLE_PATH.exists():
            with open(LORE_BIBLE_PATH, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                self.data = {k: set(v) if isinstance(v, list) else v for k, v in loaded.items()}

    def save(self):
        to_save = {k: list(v) if isinstance(v, set) else v for k, v in self.data.items()}
        with open(LORE_BIBLE_PATH, 'w', encoding='utf-8') as f:
            json.dump(to_save, f, indent=4, ensure_ascii=False)
            
    def append_lore(self, new_lore):
        """Merges extracted lore from the LLM into the bible."""
        if not new_lore: return
        for category in ["characters", "factions", "locations", "mechanics"]:
            if category in new_lore and isinstance(new_lore[category], list):
                for item in new_lore[category]:
                    self.data[category].add(item)

class DataProcessor:
    def __init__(self, file_path):
        self.file_path = file_path
        self.df = pd.read_excel(file_path)
        self.id_col, self.orig_col, self.trans_col = self._detect_columns()

    def _detect_columns(self):
        cols = self.df.columns.tolist()
        id_c, orig_c, trans_c = None, None, None
        
        for c in cols:
            c_lower = str(c).lower()
            if 'id' in c_lower or 'key' in c_lower:
                id_c = c
            elif '(origin)' in c_lower:
                orig_c = c
                
        if orig_c:
            base_name = orig_c.replace('(Origin)', '').replace('(origin)', '')
            for c in cols:
                if c != orig_c and c.startswith(base_name):
                    trans_c = c
                    break
        
        return id_c, orig_c, trans_c

    def process_placeholders(self, text):
        if not isinstance(text, str):
            return text, []
        placeholders = PLACEHOLDER_PATTERN.findall(text)
        masked_text = text
        for i, p in enumerate(placeholders):
            masked_text = masked_text.replace(p, f"__TAG_{i}__")
        return masked_text, placeholders

    def restore_placeholders(self, masked_text, placeholders):
        if not isinstance(masked_text, str):
            return masked_text
        restored = masked_text
        for i, p in enumerate(placeholders):
            restored = restored.replace(f"__TAG_{i}__", p)
        return restored

    def save(self):
        self.df.to_excel(self.file_path, index=False)

class AI_Translator:
    def __init__(self, lore_bible):
        self.lore_bible = lore_bible
        # Requires OPENROUTER_API_KEY environment variable
        api_key = os.environ.get("OPENROUTER_API_KEY")
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key
        )
        self.model = 'deepseek/deepseek-v4-flash'
        
    def translate_batch(self, batch_map):
        """Translates a dictionary of {id: text} in one API call and extracts lore."""
        if not batch_map:
            return {}
            
        prompt = (
            "You are a professional localization translator for a dark fantasy RPG game (Sands of Salzaar). "
            "Translate the following JSON map of strings from Chinese to English. Maintain a serious, ancient, and immersive tone. "
            "DO NOT modify any '__TAG_X__' markers.\n\n"
            "Return ONLY a valid JSON object with TWO keys:\n"
            "1. 'translations': A JSON object where keys are the exact same IDs provided, and values are the English translations.\n"
            "2. 'lore': A JSON object with arrays for 'characters', 'factions', 'locations', and 'mechanics' containing any notable proper nouns you extracted.\n\n"
            f"Strings to translate:\n{json.dumps(batch_map, ensure_ascii=False)}"
        )
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
            )
            
            response_text = response.choices[0].message.content.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:-3].strip()
            elif response_text.startswith("```"):
                response_text = response_text[3:-3].strip()
                
            parsed = json.loads(response_text)
            
            # Save the extracted lore to the bible
            if "lore" in parsed:
                self.lore_bible.append_lore(parsed["lore"])
                
            return parsed.get("translations", batch_map)
            
        except Exception as e:
            print(f"API Error during translation: {e}.")
            return batch_map # Fallback to original on failure

def run_translation_pipeline():
    print("Starting DesertLegend English Translation Mod Pipeline via OpenRouter...")
    lore_bible = LoreBible()
    translator = AI_Translator(lore_bible)
    
    excel_files = list(LOCALIZATION_DIR.glob("*.xlsx"))
    print(f"Found {len(excel_files)} Excel files to process.")

    for file_path in excel_files:
        print(f"\nProcessing: {file_path.name}")
        processor = DataProcessor(file_path)
        
        if not all([processor.id_col, processor.orig_col, processor.trans_col]):
            print(f"  Skipping: Could not dynamically map columns.")
            continue
            
        # 1. Collect all texts that need translation
        pending_translations = {}
        row_metadata = {}
        
        for idx, row in processor.df.iterrows():
            orig_val = row[processor.orig_col]
            if pd.isna(orig_val): continue
            
            alts = str(orig_val).split('|')
            for alt_idx, alt_text in enumerate(alts):
                if not alt_text.strip(): continue
                
                masked, tags = processor.process_placeholders(alt_text)
                unique_id = f"{idx}_{alt_idx}"
                pending_translations[unique_id] = masked
                row_metadata[unique_id] = {"idx": idx, "alt_idx": alt_idx, "tags": tags}

        # 2. Process in Batches
        items = list(pending_translations.items())
        total_batches = (len(items) + BATCH_SIZE - 1) // BATCH_SIZE
        
        translated_results = {}
        for i in range(0, len(items), BATCH_SIZE):
            batch_items = dict(items[i:i+BATCH_SIZE])
            batch_num = (i // BATCH_SIZE) + 1
            print(f"  Translating Batch {batch_num}/{total_batches} ({len(batch_items)} items)...")
            
            batch_results = translator.translate_batch(batch_items)
            translated_results.update(batch_results)

        # 3. Re-assemble back into the DataFrame
        for idx, row in processor.df.iterrows():
            orig_val = row[processor.orig_col]
            if pd.isna(orig_val): continue
            
            alts = str(orig_val).split('|')
            new_alts = []
            
            for alt_idx, alt_text in enumerate(alts):
                if not alt_text.strip(): 
                    new_alts.append(alt_text)
                    continue
                    
                unique_id = f"{idx}_{alt_idx}"
                meta = row_metadata[unique_id]
                trans_masked = translated_results.get(unique_id, pending_translations[unique_id])
                trans_restored = processor.restore_placeholders(trans_masked, meta["tags"])
                new_alts.append(trans_restored)
                
            processor.df.at[idx, processor.trans_col] = '|'.join(new_alts)
            
        processor.save()
        lore_bible.save()
        print(f"Successfully saved {file_path.name} and updated Lore Bible")
        
    print("\nPipeline complete!")

if __name__ == "__main__":
    run_translation_pipeline()
