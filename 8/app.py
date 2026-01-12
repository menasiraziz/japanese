import streamlit as st
import os
import json
from datetime import datetime, timedelta

# --- CONFIG ---
DATA_DIR = "data"
INPUT_JSON = "8/words.json" 
LISTS = ["hard", "difficult", "easy", "unknown"]
REPEAT_INTERVALS = {
    "difficult": 5,   # minutes
    "hard": 1,
    "easy": 120,
    "unknown": 1,   # 30 seconds
}

# --- UTILS ---
def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)

def load_input_data():
    """Load the source data from the JSON file."""
    if os.path.exists(INPUT_JSON):
        with open(INPUT_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def load_list(list_name):
    path = os.path.join(DATA_DIR, f"{list_name}.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_list(list_name, data):
    path = os.path.join(DATA_DIR, f"{list_name}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_next_card(lists):
    """Finds the first example (card) ready for review."""
    now = datetime.now().timestamp()
    for list_name in LISTS:
        for entry in lists[list_name]:
            if now >= entry["next_review"]:
                return entry, list_name
    return None, None

def move_card(card_entry, from_list, to_list, lists):
    """Moves a specific example card to a new list."""
    # Remove specific sentence from old list
    # We identify the card by its unique 'sentence' string
    lists[from_list] = [w for w in lists[from_list] if w["sentence"] != card_entry["sentence"]]
    
    # Set new review time
    interval = REPEAT_INTERVALS[to_list]
    next_review = (datetime.now() + timedelta(minutes=interval)).timestamp()
    
    # Update the card's timestamp
    card_entry["next_review"] = next_review
    
    lists[to_list].append(card_entry)
    
    # Save all lists
    for l in LISTS:
        save_list(l, lists[l])

def add_new_examples_to_lists(input_data, lists):
    """
    Flattens the input JSON. 
    Instead of adding 'Words', it adds individual 'Examples' to the lists.
    """
    # Gather all currently tracked sentences to prevent duplicates
    all_tracked_sentences = set()
    for l_name in LISTS:
        for entry in lists[l_name]:
            # We use the unique sentence string as the ID
            all_tracked_sentences.add(entry["sentence"])
    
    changes_made = False
    
    for word_group in input_data:
        root_word = word_group["word"]
        
        for example in word_group["examples"]:
            if example["sentence"] not in all_tracked_sentences:
                # Create a flat object for this specific example
                new_card = example.copy()
                new_card["root_word"] = root_word # Keep reference to the root word
                new_card["next_review"] = datetime.now().timestamp()
                
                lists["unknown"].append(new_card)
                all_tracked_sentences.add(example["sentence"])
                changes_made = True
            
    if changes_made:
        save_list("unknown", lists["unknown"])

# --- MAIN APP ---
ensure_dirs()

# Load lists
lists = {l: load_list(l) for l in LISTS}

# Load input data and update lists if necessary
input_data = load_input_data()
if input_data:
    add_new_examples_to_lists(input_data, lists)
else:
    st.warning(f"Could not find {INPUT_JSON}. Please create the file with the JSON data.")

st.title("Romaji SRS Quiz (By Example)")

# Get next card (example) to review
if "current_card" not in st.session_state or "current_list" not in st.session_state:
    card_entry, current_list = get_next_card(lists)
    
    if card_entry:
        st.session_state["current_card"] = card_entry
        st.session_state["current_list"] = current_list
else:
    card_entry = st.session_state["current_card"]
    current_list = st.session_state["current_list"]

if card_entry:
    # Display the Quiz Question
    st.markdown(f"### Quiz: {card_entry['romaji']}")
    
    if "show" not in st.session_state:
        st.session_state["show"] = False

    if not st.session_state["show"]:
        st.write("What does this mean?")
        if st.button("Show Answer"):
            st.session_state["show"] = True
            st.rerun()
    else:
        # Display Answer Details
        st.markdown("---")
        st.success(f"**English:** {card_entry['english']}")
        st.info(f"**Meaning Breakdown:** {card_entry['romaji_meaning']}")
        st.write(f"**Original Sentence:** {card_entry['sentence']}")
        # We stored the root word separately when flattening the list
        st.caption(f"Root Word: {card_entry['root_word']}")
        
        st.markdown("---")
        st.write("How difficult was this example?")

        col1, col2, col3, col4 = st.columns(4)
        
        def reset_state():
            st.session_state["show"] = False
            del st.session_state["current_card"]
            del st.session_state["current_list"]

        with col1:
            if st.button("Difficult (5m)"):
                move_card(card_entry, current_list, "difficult", lists)
                reset_state()
                st.rerun()
                
        with col2:
            if st.button("Hard (1m)"):
                move_card(card_entry, current_list, "hard", lists)
                reset_state()
                st.rerun()
                
        with col3:
            if st.button("Easy (1h)"):
                move_card(card_entry, current_list, "easy", lists)
                reset_state()
                st.rerun()
                
        with col4:
            if st.button("Unknown (1m)"):
                move_card(card_entry, current_list, "unknown", lists)
                reset_state()
                st.rerun()

else:
    st.success("No examples to review right now! 🎉")

st.markdown("---")
st.write("Examples count per list:")
cols = st.columns(len(LISTS))
for i, l in enumerate(LISTS):
    with cols[i]:
        st.metric(label=l.capitalize(), value=len(lists[l]))