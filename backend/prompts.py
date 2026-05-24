from backend.prompt_loader import load_prompt_template

DEBRIEF_INSTRUCTIONS = load_prompt_template('debrief_instructions')
FINAL_SUMMARY_REQUEST = load_prompt_template('final_summary').replace('{transcript_text}', '').strip()
