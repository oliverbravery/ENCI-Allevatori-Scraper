# ENCI Dog Breed Web Scraper
⚠️ **Warning: This project is no longer actively maintained.**

This project scrapes the Italian ENCI website utilising multiple processes to gather information about dog breeds, breeders, members, and areas of Italy. The scraped data is stored in a MySQL database locally.

## Installation
1. Clone the repository: `git clone https://github.com/oliverbravery/allevatori.git`
2. Install the required dependencies: `pip install -r requirements.txt`

## Usage
1. Run the main script: `python main.py`
2. The script will start scraping the ENCI website and populate a MySQL database (stored in the root of the directory as `storage.db`) with the gathered data.

## Contributing
Contributions are welcome! If you find any issues or have suggestions for improvements, please open an issue or submit a pull request.

## License
This project is licensed under the [MIT License](LICENSE).

## Acknowledgements
- [ENCI website](https://www.enci.it/)
- [MySQL](https://www.mysql.com/)
