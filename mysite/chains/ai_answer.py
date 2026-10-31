from mysite.base_knowledge import PAYMENT_WORDS, PAYMENT_INTRO, GENERAL_INTRO, PAYMENT_END, GENERAL_END

def answer(text, facts=None):
    payment = any(word in text.casefold() for word in PAYMENT_WORDS)
    parts = [PAYMENT_INTRO if payment else GENERAL_INTRO]
    cleaned = (facts or '').strip().rstrip(' .,!?:;…。\t\r\n')
    if cleaned:
        parts.append(f'По нашим данным: {cleaned}.')
    parts.append(PAYMENT_END if payment else GENERAL_END)
    return {'text_draft': ' '.join(parts), 'review': True}
