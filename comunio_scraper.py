import requests
import argparse
import re
import csv
import os
from datetime import datetime
from bs4 import BeautifulSoup

news_file_path = "news_html.txt"
standings_file_path = "standings_html.txt"
transfers_file_path = "transfers.csv"
balance_file_path = "balances.csv"
boni_file_path = "boni.csv"

#latest_date = datetime.strptime("7/22/24", "%m/%d/%y")
latest_date = datetime.strptime("1/1/24", "%m/%d/%y")
latest_bonus = datetime.strptime("1/1/24", "%m/%d/%y")

player_names = ["Victor", "Passi", "Mike", "fifty", "Lennard", "Darius", "Christian", "Johannes", "Rouven", "Tennef", "Moritz"]
starting_balance = "20000000"

def parse_arguments():
    parser = argparse.ArgumentParser(description="Scrape transfer details from Comunio. Paste the HTML source of the comunnio dashboard into the \"news_html.txt\" file to extract new transfer details when running the script. Paste the HTML source of the standings page into the \"standings_html_txt\" file.")
    parser.add_argument("--mode", type=str, required=False, default="default", help="Set the mode to run. Use \"reset\" to reset all transfers and balances, use \"default\" to extract new transfers and calculate all players balances. ")
    parser.add_argument("--date", type=str, required=False, default="None", help="Override start date for extracting transfers. Use the Format M/D/YY.")
    #parser.add_argument("--csv", type=str, required=False, help="The output CSV file name.")
    return parser.parse_args()


def extract_news(news_file_path):
    with open(news_file_path, "r") as file:
        html_content = file.read()

    soup = BeautifulSoup(html_content, "html.parser")
    transfers, boni = [], []

    print("Extracting transfers...")
    for daily_news_body in soup.find_all("div", class_="news_body_per_day animatable fold-animation"):
        for transfer_container in daily_news_body("div", attrs={"ng-if": "entry.type === 'TRANSACTION_TRANSFER'"}):
            for transfer in transfer_container("span", attrs={"translate": ""}):
                try:
                    player_tag = transfer.find("a", href=re.compile(r"/bundesliga/players/"))
                    player_name = player_tag.text if player_tag else None

                    text = transfer.get_text()
                    amount_match = re.search(r"transfers for ([\d,]+)", text)
                    amount = amount_match.group(1).replace(",", "") if amount_match else None

                    news_date = daily_news_body.find("div", class_="news_body_left news_date").text

                    from_computer_match = re.search(r"from (\w+)", text)
                    to_computer_match = re.search(r"to (\w+)", text)

                    if from_computer_match:
                        source_name = from_computer_match.group(1) if from_computer_match else None
                    else:
                        source_name = None

                    if to_computer_match:
                        target_name = to_computer_match.group(1) if to_computer_match else None
                    else:
                        target_name = None

                    if "Computer" in [source_name, target_name]:
                        if source_name == "Computer":
                            source_name = None
                        if target_name == "Computer":
                            target_name = None

                    if (player_name != None):
                        transfers.append({
                                "Date": news_date,
                                "Source_Name": source_name,
                                "Target_Name": target_name,
                                "Amount": amount,
                                "Player_Name": player_name
                        })
                except AttributeError:
                    continue

        for single_news_cont in daily_news_body("div", class_="single_news_container"):
            news_date = daily_news_body.find("div", class_="news_body_left news_date").text

            for admin_msg in single_news_cont("div", class_="news_text", attrs={"ng-class": "{'news_text_message': entry.type === 'OTHER' && entry.title === 'MESSAGE'}"}):
                news_text = admin_msg.text

                amount_match = re.search(r'Gutschrift:\s*([\d,.]+)', news_text)
                amount = amount_match.group(1).replace(".","") if amount_match else None

                player_match = re.search(r'wurden\s*([\w\s]+)\s*vom\s*Communityleiter', news_text)
                player_full_name = player_match.group(1) if player_match else None
                player_name = player_full_name.split()[0] if player_full_name else None

                if player_name:
                    boni.append({
                        "Name": player_name,
                        "Amount": amount,
                        "Date": news_date
                    })

    transfers.sort(key=lambda x: parse_date(x["Date"]))
    boni.sort(key=lambda x: parse_date(x["Date"]))
    return transfers, boni

def write_csv(transfers_file_path, balance_file_path, boni_file_path, latest_date, latest_bonus, transfers, boni, team_values):
    try:
        with open(transfers_file_path, mode="r") as csvfile:
            reader = csv.DictReader(csvfile)
            last_row = None
            for row in reader:
                last_row = row
            if last_row:
                latest_date = datetime.strptime(last_row["Date"], "%m/%d/%y ")
    except FileNotFoundError as e:
        print(e)

    try:
        with open(boni_file_path, mode="r") as csvfile:
            reader = csv.DictReader(csvfile)
            last_row = None
            for row in reader:
                last_row = row
            if last_row:
                latest_bonus = datetime.strptime(last_row["Date"], "%m/%d/%y ")
    except FileNotFoundError as e:
        print(e)

    new_transfers = [t for t in transfers if datetime.strptime(t["Date"], "%m/%d/%y ") > latest_date] if latest_date else transfers
    new_boni = [b for b in boni if datetime.strptime(b["Date"], "%m/%d/%y ") > latest_bonus] if latest_bonus else boni
    print(f"New transfers since {latest_date}:")
    if new_transfers:
        for t in new_transfers:
            print(t)
    else:
        print("None.")

    print(f"New boni since {latest_bonus}:")
    if new_boni:
        for b in new_boni:
            print(b)
    else:
        print("None.")
    

    with open(transfers_file_path, mode="a", newline="") as csvfile:
        fieldnames = ["Date", "Source_Name", "Target_Name", "Amount", "Player_Name"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if latest_date is None:
            writer.writeheader()
        for transfer in new_transfers:
            writer.writerow(transfer)

    with open(boni_file_path, mode="a", newline="") as csvfile:
        fieldnames = ["Name", "Amount", "Date"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if latest_bonus is None:
            writer.writeheader()
        for bonus in new_boni:
            writer.writerow(bonus)

    balances = []
    with open(balance_file_path, mode="r", newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            balances.append(row)

    for b in balances:
        for nt in new_transfers:
            if (nt["Source_Name"] == b["Name"]):
                new_balance = int(b["Balance"]) + int(nt["Amount"].replace(",", ""))
                b["Balance"] = new_balance
            elif (nt["Target_Name"] == b["Name"]):
                new_balance = int(b["Balance"]) - int(nt["Amount"].replace(",", ""))
                b["Balance"] = new_balance
        for tv in team_values:
            if (b["Name"] == tv["Name"]):
                b["Team value"] = tv["Team value"]
        for bonus in new_boni:
            if (b["Name"] == bonus["Name"]):
                new_balance = int(b["Balance"]) + int(bonus["Amount"])
                b["Balance"] = new_balance


        b["Max. offer"] = int(b["Balance"]) + int(int(b["Team value"]) / 2)

    print(f"New Balances:")
    for b in balances:
        print(b)

    with open(balance_file_path, mode="w", newline="") as csvfile:
        fieldnames = ["Name", "Balance", "Team value", "Max. offer"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for b in balances:
            writer.writerow(b)

def extract_team_values(standings_file_path):
    with open(standings_file_path, "r") as file:
        html_content = file.read()

    soup = BeautifulSoup(html_content, "html.parser")
    team_values = []

    print("Extracting team values...")
    for click_area in soup.find_all("div", class_="click-and-hover-area"):
        try:
            human_tag = click_area.find("div", class_="name text-to-slide whitespace_nowrap")
            human_name = human_tag.text.split()[0]

            value_tag = click_area.find("div", class_="teamvalue text_oswald text_align_right")
            value = value_tag.text.replace(",","")

            team_values.append({
                "Name": human_name,
                "Team value": value
            })

        except Exception as e:
            print(e)
    
    #print(team_values)
    return team_values
                                

def reset_balances(balance_file_path):
    balances = [{"Name": name, "Balance": starting_balance, "Team value": "0", "Max. offer": "0"} for name in player_names]
    with open(balance_file_path, mode="w", newline="") as csvfile:
        fieldnames = ["Name", "Balance", "Team value", "Max. offer"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for b in balances:
            writer.writerow(b)

def reset_transfers(transfers_file_path):
    if os.path.exists(transfers_file_path):
        os.remove(transfers_file_path)

    with open(transfers_file_path, "w") as csvfile:
        fieldnames = ["Date", "Source_Name", "Target_Name", "Amount", "Player_Name"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

def reset_boni(boni_file_path):
    if os.path.exists(boni_file_path):
        os.remove(boni_file_path)

    with open(boni_file_path, "w") as csvfile:
        fieldnames = ["Name", "Amount", "Date"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()



def parse_date(date_str):
    return datetime.strptime(date_str.strip(), "%m/%d/%y")

def get_html():
    #response = requests.get(url, headers=headers)

    #print(response)
    #print(f"encoding:{response.encoding}")
    #print(response.content)
    pass

def main():
    args = parse_arguments()
    mode = args.mode

    global latest_date
    if (args.date != "None"):
        latest_date = datetime.strptime(args.date, "%m/%d/%y")

    print(latest_date)

    if mode == "default":
        transfers, boni = extract_news(news_file_path)
        team_values = extract_team_values(standings_file_path)
        write_csv(transfers_file_path, balance_file_path, boni_file_path, latest_date, latest_bonus, transfers, boni, team_values)
    elif mode == "reset":
        print("Resetting everything.")
        reset_balances(balance_file_path)
        reset_transfers(transfers_file_path)
        reset_boni(boni_file_path)
    elif mode == "get_html":
        get_transfer_html()
    else:
        print("Undefined mode.")

    
if __name__ == "__main__":
    main()
