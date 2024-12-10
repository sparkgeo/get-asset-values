import logging

import pystac_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StacSearch:
    def __init__(
        self,
        catalog_url: str,
        start_date: str,
        end_date: str,
        stac_query: str,
        collection: str,
        max_items: int,
    ):
        self.catalog_url = catalog_url
        self.catalog = self.open_catalog()
        self.start_date = start_date
        self.end_date = end_date
        self.query = stac_query
        self.collection = collection
        self.max_items = max_items
        self.search = self.search_catalog()
        self.results = self.get_search_results()
        self.number_of_results = len(self.results)

    def open_catalog(self) -> pystac_client.Client:
        """
        Opens a STAC catalog with the provided URL and authorization headers.

        Args:
            catalog_url (str): The URL of the STAC catalog to open.

        Returns:
            pystac_client.Client: The opened STAC catalog client.
        """
        logger.info(f"Opening catalog at {self.catalog_url}")
        catalog = pystac_client.Client.open(self.catalog_url)
        return catalog

    def search_catalog(self) -> pystac_client.ItemSearch:
        """
        Searches the STAC catalog with the given parameters.

        Args:
            catalog (pystac_client.Client): The STAC catalog client.
            time_range (str): The datetime range for the search.
            query (dict): The query parameters for the search.
            collection (str, optional): The collection to search within.
            max_items (int, optional): The maximum number of items to return.

        Returns:
            pystac_client.ItemSearch: The search results.
        """
        time_range = f"{self.start_date}/{self.end_date}"
        logger.info(
            "Searching catalog for items with time"
            f"range {time_range} and query {self.query}"
        )
        if self.query is None:
            search_params = {"datetime": time_range}
        else:
            cq2_filter = self.query_to_filter()
            search_params = {"datetime": time_range, "filter": cq2_filter}
        if self.collection:
            search_params["collections"] = [self.collection]
        if self.max_items:
            search_params["max_items"] = self.max_items
        search = self.catalog.search(**search_params)
        return search

    def get_search_results(self) -> list:
        """
        Retrieves asset hrefs from search results.

        Args:
            search (pystac_client.ItemSearch): The search results.

        Returns:
            list: A list of asset href values.
        """
        logger.info("Getting search results")
        results = []
        for item in self.search.items():
            results.append(item.get_self_href())
        return results

    def query_to_filter(self) -> dict:
        """
        Converts a query dictionary into a CQL2 JSON filter.

        Args:
            query (dict): A dictionary where keys are property names and
            values are the desired values.

        Returns:
            dict: A CQL2 JSON filter combining all conditions with an 'and' operator.
        """
        filters = []
        for key, value in self.query.items():
            filters.append(
                {
                    "op": "=",
                    "args": [{"property": f"properties.{key}"}, value],
                }
            )
        return {"op": "and", "args": filters}
