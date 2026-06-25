from mcp.server.fastmcp import FastMCP
from playwright.async_api import TimeoutError as PlaywrightTimeout
from playwright.async_api import async_playwright
from playwright.async_api import async_playwright, Browser, Page, Playwright

mcp = FastMCP("weather-Israel")

"""
שרת MCP לשליפת תחזית מזג אוויר ישראלית מאתר weather2day.co.il,
באמצעות Playwright (במקום API רשמי).

תהליך השליפה מחולק לארבעה Tools שיש להריץ לפי הסדר:
1. open_weather_forecast_israel       - פתיחת הדפדפן וניווט לדף
2. enter_weather_forecast_city_israel  - הזנת שם העיר
3. select_weather_forecast_city_israel - בחירת העיר מהרשימה
4. get_weather_forecast_content_israel - חילוץ תוכן התחזית כטקסט

כל ה-Tools פועלים על אותו דפדפן/דף משותף (ראו _BrowserState),
ולכן יש להריץ אותם בזה אחר זה, בסדר הזה, בתוך אותה שיחה.
"""

FORECAST_URL = "https://www.weather2day.co.il/forecast"
# === Selectors שאותרו ידנית מתוך הדף (Inspect) ===
CITY_INPUT_SELECTOR = "#city_search_forecast"
AUTOCOMPLETE_LIST_SELECTOR = "#city_search_forecastautocomplete-list"
AUTOCOMPLETE_FIRST_ITEM_SELECTOR = f"{AUTOCOMPLETE_LIST_SELECTOR} > div:first-child"

class _BrowserState:

    """
    מחזיקה את ה-instance של הדפדפן/הדף בין קריאות נפרדות ל-Tools.
    כל קריאה ל-Tool מגיעה מה-LLM בנפרד, ולכן צריך state ברמת המודול
    כדי ששלושת הפונקציות (open / enter / select) יוכלו לפעול על
    אותו דפדפן ואותו דף ברצף.
    """
    def __init__(self) -> None:
        self.playwright: Playwright | None = None
        self.browser: Browser | None = None
        self.page: Page | None = None

    @property
    def is_open(self) -> bool:
        return self.page is not None and not self.page.is_closed()


_state = _BrowserState()

@mcp.tool()
async def open_weather_forecast_israel() -> str:
    """
    שלב 1 מתוך תהליך שליפת תחזית: פותחת דפדפן ומנווטת לדף תחזית
    מזג האוויר באתר weather2day.co.il.
    """
    if _state.is_open:
        await _state.page.goto(FORECAST_URL, wait_until="domcontentloaded")
        return f"דף התחזית כבר היה פתוח - נווטתי מחדש אל {FORECAST_URL}"

    _state.playwright = await async_playwright().start()
    _state.browser = await _state.playwright.chromium.launch(headless=False)
    _state.page = await _state.browser.new_page()

    await _state.page.goto(FORECAST_URL, wait_until="domcontentloaded")
    await _state.page.bring_to_front()

    return f"הדפדפן נפתח בהצלחה ונווט לדף התחזית: {FORECAST_URL}"

@mcp.tool()
async def enter_weather_forecast_city_israel(city: str) -> str:
    """
    שלב 2 מתוך תהליך שליפת תחזית: מקבלת שם עיר בעברית ומזינה אותה
    בשדה החיפוש בדף, ומחכה לרשימת הצעות מתאימות.

    Args:
        city: שם העיר להזנה בשדה החיפוש (לדוגמה: "תל אביב", "בני ברק").
    """
    if not _state.is_open:
        return "שגיאה: הדפדפן לא פתוח. יש להריץ קודם את open_weather_forecast_israel."

    page = _state.page

    try:
        await page.click(CITY_INPUT_SELECTOR)
        await page.fill(CITY_INPUT_SELECTOR, "")
        await page.type(CITY_INPUT_SELECTOR, city, delay=80)

        await page.wait_for_selector(
            AUTOCOMPLETE_FIRST_ITEM_SELECTOR, timeout=5000, state="visible"
        )
    except PlaywrightTimeout:
        return (
            f"הוקלד '{city}' בשדה החיפוש, אך רשימת ההצעות לא נטענה בזמן. "
            "ייתכן ששם העיר שגוי או שיש צורך לנסות שוב."
        )

    return f"הוקלד '{city}' בשדה החיפוש, ורשימת ההצעות נטענה בהצלחה."
    
@mcp.tool()
async def select_weather_forecast_city_israel() -> str:
    """
    שלב 3 מתוך תהליך שליפת תחזית: בוחרת את ההצעה הראשונה מתוך רשימת
    הערים שהוצעה, וגורמת לדף להתרענן עם תחזית מזג האוויר לעיר שנבחרה.
    """ 
    if not _state.is_open:
        return "שגיאה: הדפדפן לא פתוח. יש להריץ קודם את open_weather_forecast_israel."

    page = _state.page

    try:
        await page.wait_for_selector(
            AUTOCOMPLETE_FIRST_ITEM_SELECTOR, timeout=3000, state="visible"
        )
        await page.click(AUTOCOMPLETE_FIRST_ITEM_SELECTOR)

        await page.wait_for_load_state("domcontentloaded")
    except PlaywrightTimeout:
        return (
            "שגיאה: לא נמצא פריט ברשימת ההצעות. "
            "יש לוודא שהוקלד שם עיר קודם באמצעות enter_weather_forecast_city_israel."
        )

    return "העיר נבחרה בהצלחה מתוך הרשימה, והדף התרענן עם תחזית מזג האוויר עבורה."


@mcp.tool()
async def get_weather_forecast_content_israel() -> str:
    """
    שלב 4 (אחרון) מתוך תהליך שליפת תחזית: מחלצת מהדף הפתוח את תוכן
    התחזית הנוכחית ואת התחזית השעתית של היום, ומחזירה אותם כטקסט
    קריא ל-LLM.
    """
    if not _state.is_open:
        return "שגיאה: הדפדפן לא פתוח. יש להריץ קודם את open_weather_forecast_israel."

    page = _state.page

    try:
        current_weather_locator = page.locator(".current-weather").first
        await current_weather_locator.wait_for(timeout=5000, state="visible")
        current_weather_text = await current_weather_locator.inner_text()
    except PlaywrightTimeout:
        current_weather_text = "לא נמצא בלוק תחזית נוכחית בדף."

    try:
        today_details_locator = page.locator(".hourly_forecast_container details").first
        today_summary = await today_details_locator.locator("summary").inner_text()
        today_table_text = await today_details_locator.locator("table").inner_text()
        hourly_today_text = f"{today_summary}\n{today_table_text}"
    except PlaywrightTimeout:
        hourly_today_text = "לא נמצא בלוק תחזית שעתית להיום בדף."

    return (
        "=== תחזית נוכחית ===\n"
        f"{current_weather_text}\n\n"
        "=== תחזית שעתית להיום ===\n"
        f"{hourly_today_text}"
    )




def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
