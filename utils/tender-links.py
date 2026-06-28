def build_tender_card_url(reg_number: str):
    return f"https://zakupki.gov.ru/epz/order/notice/ok20/view/common-info.html?regNumber={reg_number}"


def build_tender_print_url(reg_number: str):
    return f"https://zakupki.gov.ru/epz/order/notice/printForm/view.html?regNumber={reg_number}"