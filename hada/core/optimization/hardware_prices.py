from hada.core.config.configdb import ConfigDB


class HardwarePrices():
    """
    Represents price assignments for each hw platform (algorithm-specific). 
    """
    
    def __init__(self, configdb: ConfigDB, algorithm: str) -> None:
        """
        Initialize a HardwarePrices instance.

        Args:
            configdb (ConfigDB): configuration database containing algorithm info.
            algorithm (str): algorithm to which the constraints refer.

        Raises:
            AttributeError: if the algorithm is not available in the database.
        """

        self.db = configdb

        if algorithm not in self.db.get_algorithms():
            raise AttributeError(f'Algorithm {algorithm} not available.')
        
        self.algorithm = algorithm
        self.__price_per_hw =  {hw: price 
                                for hw, price in self.db.get_prices_per_hw(self.algorithm).items()
                                if price}


    def add_hw_price(self, hw: str, price: float | int) -> None:
        """
        Add or update the price for a hardware platform.

        Args:
            hw (str): hardware platform identifier.
            price (float | int): price value.

        Raises:
            AttributeError: if hardware is not available or price is invalid.
        """

        if hw not in self.db.get_hws(self.algorithm):
            raise AttributeError(f'Hardware platform {hw} not available for algorithm {self.algorithm}.')

        # ignore if price is None
        if price is None:
            return

        if not isinstance(price, (float, int)):
            raise AttributeError("Price must be numerical (int or float).")

        self.__price_per_hw[hw] = price


    def get_prices_per_hw(self) -> dict[str, float]:
        """
        Retrieve prices for all hardware platforms associated with the algorithm.

        Returns:
            dict[str, float]: (hardware platforms, prices).

        Raises:
            AttributeError: if prices for any hardware platforms are missing.
        """

        hws = set(self.db.get_hws(self.algorithm))
        prices = set(self.__price_per_hw.keys())

        if not hws == prices:
            raise AttributeError("Prices for all hardware platforms related to the algorithm must be specified when the target is 'price' or 'price' is constrainted.")
        
        return self.__price_per_hw
