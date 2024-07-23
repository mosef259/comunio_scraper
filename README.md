usage: comunio_scraper.py [-h] [--mode MODE] [--date DATE]

Scrape transfer details from Comunio. Paste the HTML source of the comunnio dashboard into the "news_html.txt" file to extract new transfer details when running the script. Paste the HTML source of the
standings page into the "standings_html_txt" file.

options:
  -h, --help   show this help message and exit
  --mode MODE  Set the mode to run. Use "reset" to reset all transfers and balances, use "default" to extract new transfers and calculate all players balances.
  --date DATE  Override start date for extracting transfers. Use the Format M/D/YY.
