import json
import os
from collections import Counter, defaultdict
from deep_translator import GoogleTranslator
import time

# Configuration
INPUT_DIR = 'data/input'
OUTPUT_DIR = 'data/output'

# Target encrypted words for each language with their codes
ENCRYPTED_WORDS = {
    'en': 'JYPFFQVY',
    'de': 'MJ?IGNPB',
#   'it': 'NSULROLQ',
#   'fr': 'QLEITRRC'
}

def debug_print(message, level=0):
    """Print debug message with indentation"""
    indent = "  " * level
    print(f"{indent}[DEBUG] {message}")

def ensure_directories():
    """Create input and output directories if they don't exist"""
    debug_print("Creating directories if they don't exist")
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_letter_pattern(word):
    """Get the frequency pattern of letters in a word"""
    return sorted(Counter(word.lower()).values(), reverse=True)

def get_file_path(file_type, source_lang='en', target_lang=None, word_length=None):
    """Get standardized file paths"""
    if file_type == 'translations':
        return os.path.join(OUTPUT_DIR, f'translations_{source_lang}_{target_lang}.json')
    elif file_type == 'matches':
        return os.path.join(OUTPUT_DIR, f'matches_{source_lang}_{target_lang}.json')
    elif file_type == 'matches_txt':
        return os.path.join(OUTPUT_DIR, f'matches_{source_lang}_{target_lang}.txt')
    elif file_type == 'no_matches':
        return os.path.join(OUTPUT_DIR, f'no_matches_{source_lang}_{target_lang}.txt')
    elif file_type == 'pattern':
        return os.path.join(OUTPUT_DIR, f'{source_lang}-words-{word_length}-pattern.json')
    return None

def load_json_file(filepath, default=None):
    """Load JSON file with default value if not exists"""
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default if default is not None else {}

def load_text_file(filepath):
    """Load text file into set"""
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def append_to_file(filepath, content):
    """Append content to file"""
    with open(filepath, 'a', encoding='utf-8') as f:
        f.write(content + '\n')

def check_and_save_matches(translations_batch, source_lang, target_lang, pattern_words):
    """Check for matches in a batch of translations and save them"""
    debug_print(f"Checking matches for batch of {len(translations_batch)} translations", 1)
    
    # Load existing matches and non-matches
    matches_file = get_file_path('matches', source_lang, target_lang)
    matches_txt_file = get_file_path('matches_txt', source_lang, target_lang)
    no_matches_file = get_file_path('no_matches', source_lang, target_lang)
    
    matches = load_json_file(matches_file)
    checked_words = load_text_file(no_matches_file)
    
    new_matches = {}
    for source_word, translated_word in translations_batch.items():
        if source_word not in checked_words and source_word not in matches:
            if (source_word in pattern_words[source_lang] and 
                translated_word in pattern_words[target_lang]):
                new_matches[source_word] = translated_word
                # Append to text file
                append_to_file(matches_txt_file, f"{source_word}: {translated_word}")
            else:
                # Add to checked words
                append_to_file(no_matches_file, source_word)
                checked_words.add(source_word)
    
    if new_matches:
        # Update JSON matches file
        matches.update(new_matches)
        with open(matches_file, 'w', encoding='utf-8') as f:
            json.dump(matches, f, ensure_ascii=False, indent=2)
        
        debug_print(f"Found {len(new_matches)} new matches", 2)
    
    return new_matches

def translate_and_match(source_lang='en'):
    """Translate words and incrementally check for matches"""
    debug_print("Starting translation and matching process")
    
    # Load pattern-matched words for all languages
    pattern_words = {}
    for lang in ENCRYPTED_WORDS.keys():
        word_length = len(ENCRYPTED_WORDS[lang])
        pattern_file = get_file_path('pattern', lang, word_length=word_length)
        pattern_words[lang] = set(load_json_file(pattern_file, []))
    
    # Load source words
    source_pattern_file = get_file_path('pattern', source_lang, 
                                      word_length=len(ENCRYPTED_WORDS[source_lang]))
    source_words = load_json_file(source_pattern_file, [])
    
    # Process each target language
    for target_lang in [lang for lang in ENCRYPTED_WORDS.keys() if lang != source_lang]:
        debug_print(f"Processing translations for {target_lang}")
        
        # Load existing translations
        translations_file = get_file_path('translations', source_lang, target_lang)
        translations = load_json_file(translations_file)
        
        # Initialize translator
        translator = GoogleTranslator(source=source_lang, target=target_lang)
        
        # Batch processing
        current_batch = {}
        batch_size = 10
        
        for idx, word in enumerate(source_words, 1):
            if word in translations:
                # Check match for previously translated word
                check_and_save_matches({word: translations[word]}, source_lang, target_lang, pattern_words)
                continue
                
            try:
                translated = translator.translate(word).lower()
                translations[word] = translated
                current_batch[word] = translated
                debug_print(f"Translated '{word}' to '{translated}'", 2)
                
                # Process batch if full or last word
                if len(current_batch) >= batch_size or idx == len(source_words):
                    # Save translations
                    with open(translations_file, 'w', encoding='utf-8') as f:
                        json.dump(translations, f, ensure_ascii=False, indent=2)
                    
                    # Check for matches
                    check_and_save_matches(current_batch, source_lang, target_lang, pattern_words)
                    current_batch = {}
                    time.sleep(1)  # Rate limiting
                    
            except Exception as e:
                debug_print(f"Translation error for '{word}': {str(e)}", 2)
                
        debug_print(f"Completed processing for {target_lang}")

def main():
    """Main function to process all languages and find translations"""
    debug_print("Starting word processing")
    
    ensure_directories()
    translate_and_match()
    
    debug_print("All processing complete")

if __name__ == "__main__":
    main()