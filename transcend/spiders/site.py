from urllib.parse import urlsplit, urlencode, unquote, urljoin, urlunparse
from urllib.parse import parse_qsl as queryparse

import scrapy

from transcend.items import *


def grouper(n, iterable):
    args = [iter(iterable)] * n
    return zip(*args)


class BaseSpider(scrapy.Spider):
    allowed_domains = [
        'transcend-info.com',
        'www.transcend-info.com',
        'us.transcend-info.com',
    ]

    def parse(self, response: scrapy.http.Response):
        raise NotImplemented


class ManufacturerSpider(BaseSpider):
    """
    Get memory modules for certain manufacturer
    """

    name = 'manufacturer'

    start_urls = [
        'https://us.transcend-info.com/support/authenticator?url=https://us.transcend-info.com/Support/compatibility',
        # 'https://us.transcend-info.com/Support/compatibility',
    ]

    manufacturer = None

    def __init__(self, manufacturer: str = ""):
        if manufacturer == "":
            manufacturer = None

        if manufacturer is None:
            raise ValueError("Invalid manufacturer given")

        self.manufacturer = manufacturer

    def parse(self, response: scrapy.http.Response):
        """
        GET
        Authentication for session ID for search form
        The search form becomes available after auth (next POST page)
        """

        # Authenticate
        yield scrapy.FormRequest.from_response(
            response,
            callback=self.parse_search_form,
            meta={
                "dont_cache": True,
            },
        )

    def parse_search_form(self, response: scrapy.http.Response):
        """
        POST
        Search for list of motherboard manufacturers
        """

        form = response.xpath("//form[@id='form1']")
        if form is None:
            raise ValueError("Search form not found")

        submit = dict(queryparse(response.request.body.decode('utf8')))

        submit.update({
            "ctl00$sm": "ctl00$Content$UpdatePanel1|ctl00$Content$Comp_Brand",
            "ctl00$search": "",
            "ctl00$Content$Comp_Device": "13",  # 13 = motherboard
            "ctl00$Content$Comp_Brand": "-1",
            "ctl00$Content$Comp_Series": "-1",
            "ctl00$Content$Comp_Module": "-1",
            "hiddenInputToUpdateATBuffer_CommonToolkitScripts": "1",
            "__EVENTTARGET": "ctl00$Content$Comp_Brand",
            "__EVENTARGUMENT": "",
            "__LASTFOCUS": "",
        })

        for forminput in form.xpath(".//input"):
            k = forminput.xpath("./@name").get()
            if k in ['ctl00$Content$BT_searchID', 'ctl00$BT_search']:
                continue

            v = forminput.xpath("./@value").get() or ""

            submit[k] = v

        yield scrapy.FormRequest.from_response(
            response,
            callback=self.parse_list_brands,
            formdata=submit,
            meta={
                "dont_cache": True,
            },
        )

    def parse_list_brands(self, response: scrapy.http.Response):
        """
        POST
        """
        form = response.xpath("//form[@id='form1']")
        if form is None:
            raise ValueError("Search form not found")

        if form.xpath(".//select[@name='ctl00$Content$Comp_Device']/option[@value='13']/@selected").get() is None:
            raise ValueError("Motherboard not selected")

        submit = dict(queryparse(response.request.body.decode('utf8')))

        # Select manufacturer
        manufacturerid = form.xpath(
            ".//select[@name='ctl00$Content$Comp_Brand']/option[text()='" + self.manufacturer + "']/@value").get()

        if manufacturerid is None:
            raise ValueError("Manufacturer not found")

        submit.update({
            "ctl00$sm": "ctl00$Content$UpdatePanel1|ctl00$Content$Comp_Series",
            "ctl00$search": "",
            "ctl00$Content$Comp_Device": "13",  # 13 = motherboard
            "ctl00$Content$Comp_Brand": manufacturerid,  # 205 = Supermicro
            "ctl00$Content$Comp_Series": "-1",
            "ctl00$Content$Comp_Module": "-1",
            "hiddenInputToUpdateATBuffer_CommonToolkitScripts": "1",
            "__EVENTTARGET": "ctl00$Content$Comp_Series",
            "__EVENTARGUMENT": "",
            "__LASTFOCUS": "",
        })

        for forminput in form.xpath(".//input"):
            k = forminput.xpath("./@name").get()
            if k in ['ctl00$Content$BT_searchID', 'ctl00$BT_search']:
                continue

            v = forminput.xpath("./@value").get() or ""

            submit[k] = v

        yield scrapy.FormRequest.from_response(
            response,
            callback=self.parse_list_series,
            formdata=submit,
            meta={
                "dont_cache": True,
            },
        )

    def parse_list_series(self, response: scrapy.http.Response):
        """
        POST
        """
        form = response.xpath("//form[@id='form1']")
        if form is None:
            raise ValueError("Search form not found")

        if form.xpath(".//select[@name='ctl00$Content$Comp_Device']/option[@value='13']/@selected").get() is None:
            raise ValueError("Motherboard not selected")

        submit = dict(queryparse(response.request.body.decode('utf8')))

        if "ctl00$Content$Comp_Device" not in submit:
            raise KeyError("ctl00$Content$Comp_Device not set")

        if "ctl00$Content$Comp_Brand" not in submit:
            raise KeyError("ctl00$Content$Comp_Brand not set")

        if form.xpath(".//select[@name='ctl00$Content$Comp_Brand']/option[@value='" +
                      submit['ctl00$Content$Comp_Brand'] + "']/@selected").get() is None:
            raise ValueError("Brand not selected")

        submit.update({
            "ctl00$sm": "ctl00$Content$UpdatePanel1|ctl00$Content$Comp_Series",
            "ctl00$search": "",
            "ctl00$Content$Comp_Series": "-1",
            "ctl00$Content$Comp_Module": "-1",
            "hiddenInputToUpdateATBuffer_CommonToolkitScripts": "1",
            "__EVENTTARGET": "ctl00$Content$Comp_Series",
            "__EVENTARGUMENT": "",
            "__LASTFOCUS": "",
        })

        for forminput in response.xpath("//input"):
            k = forminput.xpath("./@name").get()
            if k in ['ctl00$Content$BT_searchID', 'ctl00$BT_search']:
                continue

            v = forminput.xpath("./@value").get() or ""

            submit[k] = v

        for opt in form.xpath(".//select[@name='ctl00$Content$Comp_Series']/option"):
            optid = int(opt.xpath("./@value").get())
            if optid < 0:
                continue

            optname = "".join(opt.xpath(".//text()").getall()).strip()
            submit.update({
                "ctl00$Content$Comp_Series": str(optid),
            })

            yield scrapy.FormRequest.from_response(
                response,
                callback=self.parse_motherboard_list,
                formdata=submit,
                meta={
                    "dont_cache": True,
                    "series": optname,
                },
            )

    def parse_motherboard_list(self, response: scrapy.http.Response):
        """
        POST
        """
        form = response.xpath("//form[@id='form1']")
        if form is None:
            raise ValueError("Search form not found")

        submit = dict(queryparse(response.request.body.decode('utf8')))

        if "ctl00$Content$Comp_Device" not in submit:
            raise KeyError("ctl00$Content$Comp_Device not set")

        if "ctl00$Content$Comp_Brand" not in submit:
            raise KeyError("ctl00$Content$Comp_Brand not set")

        if "ctl00$Content$Comp_Series" not in submit:
            raise KeyError("ctl00$Content$Comp_Series not set")

        if form.xpath(".//select[@name='ctl00$Content$Comp_Device']/option[@value='13']/@selected").get() is None:
            raise ValueError("Motherboard not selected")

        if form.xpath(".//select[@name='ctl00$Content$Comp_Brand']/option[@value='" +
                      submit['ctl00$Content$Comp_Brand'] + "']/@selected").get() is None:
            raise ValueError("Brand not selected")

        if form.xpath(".//select[@name='ctl00$Content$Comp_Series']/option[@value='" +
                      submit['ctl00$Content$Comp_Series'] + "']/@selected").get() is None:
            raise ValueError("Series not selected")

        for prod in response.xpath("//select[@name='ctl00$Content$Comp_Module']/option"):
            prodid = int(prod.xpath("./@value").get())

            if prodid < 0:
                continue

            yield scrapy.Request(
                response.urljoin(f"/Support/compatibility/{prodid}/"),
                callback=self.parse_modules,
                meta={
                    # "dont_cache": False,
                    'series': response.meta['series'],
                },
            )

    def parse_modules(self, response: scrapy.http.Response):
        """
        GET
        We've now selected device type Motherboard, some brand and some series from that brand
        """

        curpath = urlsplit(response.url).path.strip("/")
        curpatha = curpath.split("/")

        if len(curpatha) != 3:
            raise ValueError(f"URL path '{curpath}' has invalid number of parts")

        form = response.xpath("//form[@id='form1']")
        if form is None:
            raise ValueError("Search form not found")

        # Get information for what motherboard this page is for
        device = form.xpath(".//select[@name='ctl00$Content$Comp_Device']/option/@selected/../text()").get().strip()
        brand = form.xpath(".//select[@name='ctl00$Content$Comp_Brand']/option/@selected/../text()").get().strip()
        series = form.xpath(".//select[@name='ctl00$Content$Comp_Series']/option/@selected/../text()").get().strip()
        mb = form.xpath(".//select[@name='ctl00$Content$Comp_Module']/option/@selected/../text()").get().strip()

        mb = mb.replace("Motherboard", "").strip()
        mb = mb.replace("/", ",")
        mb = mb.replace(", ", ",")

        #self.logger.info(f"MB:{mb} - Series:{series} - Brand:{brand} - Device:{device} - <URL: {response.url} >")

        modules = []

        for sect in response.xpath("//div[@id='New_Content_Pa_Result']/div[@class='Item']"):

            # Section name
            # For example "Internal SSDs" or "DRAM Modules"
            name = "".join(sect.xpath("./h4//text()").getall()).strip()

            if name != 'DRAM Modules':
                # Get only memory
                continue

            for memmod in sect.xpath(".//div[contains(@class, 'RowCon') and contains(@class, 'Body')]"):
                # Link for memory module (not a direct link to specs, only for a generic memory module listings page)
                prodlink = memmod.xpath(".//div[@class='BTNs']/a/@href").get()

                if prodlink is None:
                    raise ValueError(f"Memory module link was not found on section {name}!")

                prodinfo = memmod.xpath(".//div[contains(@class, 'Product')]")

                prodname = prodinfo.xpath("./h3/text()").get().strip()
                prodspec = prodinfo.xpath("./p[@class='Product_Spec']/text()").get().strip()
                capacity = prodinfo.xpath(".//li[contains(@class, 'label-capacity-greenborder')]/text()").get().strip()
                prodid = prodinfo.xpath(".//li[@class='Product_PN']/text()").get()

                modules.append({
                    'id': prodid,
                    'link': response.urljoin(prodlink),
                    'name': prodname,
                    'spec': prodspec,
                    'capacity': capacity,
                })

        if len(modules) == 0:
            self.logger.info(f"No memory modules found for {mb}, skipping <URL: {response.url} >")
            return

        yield Memory({
            '_manufacturer': brand,
            '_model': mb,
            '_url': response.url,
            'modules': modules,
        })
