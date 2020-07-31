# scrapy-transcend

Web crawler for ([Transcend](https://us.transcend-info.com))

## Requirements

* Python
* [Scrapy](https://scrapy.org/)

## Notes

* 1 day cache is used in `settings.py`

## Spiders

All items are downloaded as JSON in the `items/` directory.

### Memory modules for all motherboards from certain manufacturer

For example all motherboard memory modules from Supermicro's motherboards:

    scrapy crawl manufacturer -a manufacturer="SUPERMICRO"

This will generate `items/Memory/SUPERMICRO/<motherboard model>.json` which then lists all compatible memory modules for this motherboard.
