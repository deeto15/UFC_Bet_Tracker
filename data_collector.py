import time
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By

def grab_links():
    list_of_links = []
    url = "https://fightodds.io/recent-mma-events/ufc"
    driver = webdriver.Chrome()
    driver.get(url)
    time.sleep(2)

    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")

    pattern = re.compile(r"^/mma-events/.*?/odds$", re.IGNORECASE)

    links = soup.find_all("a", href=lambda x: x and pattern.match(x))
    for link in links:
        href = link.get("href")
        url = "https://fightodds.io" + href[:-5] + "/fights"
        list_of_links.append(url)
    driver.quit()
    return list_of_links

def grab_odds_links(url):
    winnerKV = {}
    individual_odds_links = []
    driver = webdriver.Chrome()
    driver.get(url)
    time.sleep(5)
    rows = driver.find_elements(By.XPATH, "//table/tbody//tr")
    for row in rows:
        # Only process rows that have "def." (completed fights)
        if "def." in row.text:
            parts = row.text.split()
            key = " ".join(parts[1:parts.index("def.")])
            list_of_keywords = ["Decision", "KO", "TKO", "Submission"]
            for keyword in list_of_keywords:
                if any(keyword in part for part in parts):
                    winnerKV[key] = keyword
                    break
            
            # Only get the link if this is a completed fight
            try:
                link = row.find_element(By.XPATH, ".//a[contains(@class, 'MuiButton-root')]")
                href = link.get_attribute("href")
                individual_odds_links.append(href)
            except:
                print(f"Warning: Could not find link for {key}")
                
    driver.quit()
    return individual_odds_links, winnerKV

def odds_gatherer(url):
    driver = webdriver.Chrome()
    driver.get(url)
    time.sleep(10)

    buttons = driver.find_elements(By.TAG_NAME, "button")
    target_button = None

    for i, btn in enumerate(buttons):
        text = btn.text.strip()
        if "prop bets" in text.lower():
            target_button = btn

    if target_button:
        print("\nClicking Prop Bets button!.\n")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_button)
        time.sleep(0.4)
        target_button.click()
    else:
        print("didnt click button god damnit ")

    time.sleep(10)
    
    final_table = []
    rows_in_header = driver.find_elements(By.XPATH, "//table/thead//tr")
    for row in rows_in_header:
        cells = row.find_elements(By.XPATH, ".//th")
        values = [c.text.strip() for c in cells]
        if len(values) > 9:
            final_table.append(values)
        
    keywords = ["wins by decision", "wins by TKO/KO", "wins by submission"]
    rows_in_body = driver.find_elements(By.XPATH, "//table/tbody//tr")
    for row in rows_in_body:
        if any(keyword in row.text for keyword in keywords):
            row_values = []
            cells = row.find_elements(By.TAG_NAME, "td")
            for cell in cells:
                text = cell.text.strip()
                if text == "":
                    row_values.append(None)
                else:
                    row_values.append(cell.text)
            if len(row_values) > 1 and "%" not in row_values[1]:
                final_table.append(row_values)
    driver.quit()
    return final_table

def filterRows(table):
    best_bets = {}
    for row in table:
        key = row[0]        
        value = row[1]        
        best_bets[key] = value
    return best_bets

def get_event_name(url):
    """
    Extracts the UFC event name from the URL.
    Example:
    https://fightodds.io/mma-events/6603/ufc-fight-night-265-tsarukyan-vs-hooker/fights
    -> "ufc-fight-night-265-tsarukyan-vs-hooker"
    """
    match = re.search(r"/([^/]+)/fights/?$", url)
    if match:
        return match.group(1)
    else:
        return "ufc-event"
      
def main():
    all_cards = grab_links()
    all_cards = [all_cards[5]]
    
    for card_url in all_cards:
        odds_url, winnerKV = grab_odds_links(card_url)
        winner_list = list(winnerKV.items())  # Convert to list to maintain order
        
        print(f"Found {len(odds_url)} odds URLs and {len(winner_list)} winners")
        
        for i, odds in enumerate(odds_url):
            if i >= len(winner_list):
                print(f"Warning: No winner info for fight {i}")
                continue
                
            winner = winner_list[i]
            print(f"\nProcessing: {winner[0]} ({winner[1]})")
            print(f"URL: {odds}")
            
            table = odds_gatherer(odds)
            betOnlineOnly = filterRows(table)
            
            # Remove the header row by checking the key
            betOnlineOnly = {k: v for k, v in betOnlineOnly.items() if k != "Props"}
            
            if not betOnlineOnly:
                print(f"No bets available for {winner[0]}")
                continue
            
            # Sort by odds value (lowest to highest)
            sorted_odds = sorted(betOnlineOnly.items(), key=lambda x: int(x[1].replace('+', '')))
            
            # Get the lowest
            selected_bets = [sorted_odds[0]]
            
            # Check if second lowest is within 50 points
            if len(sorted_odds) > 1:
                lowest_value = int(sorted_odds[0][1].replace('+', ''))
                second_value = int(sorted_odds[1][1].replace('+', ''))
                
                if second_value - lowest_value <= 50:
                    selected_bets.append(sorted_odds[1])
            
            print(f"\nSelected bets for {winner[0]} ({winner[1]}):")
            for bet, odd in selected_bets:
                print(f"  {bet}: {odd}")

main()