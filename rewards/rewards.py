from iconservice import *

TAG = 'REWARDS'
DAILY_TOKEN_DISTRIBUTION = 1000000000000000000000000
DEBUG = False
TAP = 1000000000000000000


# An interface of token to distribute daily rewards
class TokenInterface(InterfaceScore):
    @interface
    def transfer(self, _to: Address, _value: int, _data: bytes = None):
        pass

    @interface
    def symbol(self) -> str:
        pass

    @interface
    def balanceOf(self, _owner: Address) -> int:
        pass


# An interface to the game score
class GameInterface(InterfaceScore):
    @interface
    def get_batch_size(self, recip_count: int) -> int:
        pass


# An interface to the dividends score
class DividendsInterface(InterfaceScore):
    @interface
    def distribute(self) -> bool:
        pass


class Rewards(IconScoreBase):
    _WAGERS = "wagers"
    _DAY = "day"
    _EVEN_DAY = "even_day"
    _ODD_DAY = "odd_day"
    _EVEN_DAY_TOTAL = "even_day_total"
    _ODD_DAY_TOTAL = "odd_day_total"
    _WAGER_TOTAL = "wager_total"

    _DAILY_DIST = "daily_dist"
    _DIST_INDEX = "dist_index"
    _DIST_COMPLETE = "dist_complete"

    _GAME_SCORE = "game_score"
    _TOKEN_SCORE = "token_score"
    _DIVIDENDS_SCORE = "dividends_score"
    _BATCH_SIZE = "batch_size"

    _REWARDS_GONE = "rewards_gone"
    _YESTERDAYS_TAP_DISTRIBUTION = "yesterdays_tap_distribution"

    @eventlog(indexed=2)
    def FundTransfer(self, sweep_to: str, amount: int, note: str):
        pass

    @eventlog(indexed=2)
    def TokenTransfer(self, recipient: Address, amount: int):
        pass

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        Logger.debug(f'In __init__.', TAG)
        Logger.debug(f'owner is {self.owner}.', TAG)
        self._wagers = DictDB(self._WAGERS, db, value_type=int, depth=2)
        self._day_index = VarDB(self._DAY, db, value_type=int)
        self._even_day_addresses = ArrayDB(self._EVEN_DAY, db, value_type=str)
        self._odd_day_addresses = ArrayDB(self._ODD_DAY, db, value_type=str)
        self._addresses = [self._even_day_addresses, self._odd_day_addresses]
        self._even_day_total = VarDB(self._EVEN_DAY_TOTAL, db, value_type=int)
        self._odd_day_total = VarDB(self._ODD_DAY_TOTAL, db, value_type=int)
        self._daily_totals = [self._even_day_total, self._odd_day_total]
        self._wager_total = VarDB(self._WAGER_TOTAL, db, value_type=int)
        self._daily_dist = VarDB(self._DAILY_DIST, db, value_type=int)
        self._dist_index = VarDB(self._DIST_INDEX, db, value_type=int)
        self._dist_complete = VarDB(self._DIST_COMPLETE, db, value_type=bool)

        self._game_score = VarDB(self._GAME_SCORE, db, value_type=Address)
        self._token_score = VarDB(self._TOKEN_SCORE, db, value_type=Address)
        self._dividends_score = VarDB(self._DIVIDENDS_SCORE, db, value_type=Address)
        self._batch_size = VarDB(self._BATCH_SIZE, db, value_type=int)

        # rewards gone variable checks if the 500M tap token held for distribution is completed
        self._rewards_gone = VarDB(self._REWARDS_GONE, db, value_type=bool)
        self._yesterdays_tap_distribution = VarDB(self._YESTERDAYS_TAP_DISTRIBUTION, db, value_type=int)

    def on_install(self) -> None:
        super().on_install()
        self._day_index.set(0)
        self._dist_index.set(0)
        self._dist_complete.set(True)

        self._even_day_total.set(0)
        self._odd_day_total.set(0)
        self._rewards_gone.set(False)

    def on_update(self) -> None:
        super().on_update()

    @external
    def set_token_score(self, _score: Address) -> None:
        """
        Sets the tap token score address
        :param _score: Address of the token score
        :type _score: :class:`iconservice.base.address.Address`
        :return:
        """
        if self.msg.sender == self.owner:
            self._token_score.set(_score)

    @external(readonly=True)
    def get_token_score(self) -> Address:
        """
        Returns the tap token score address
        :return: Address of the tap token score
        :rtype: :class:`iconservice.base.address.Address`
        """
        return self._token_score.get()

    @external
    def set_dividends_score(self, _score: Address) -> None:
        """
        Sets the dividends distribution score address
        :param _score: Address of the dividends distribution score
        :type _score: :class:`iconservice.base.address.Address`
        :return:
        """
        if self.msg.sender == self.owner:
            self._dividends_score.set(_score)

    @external(readonly=True)
    def get_dividends_score(self) -> Address:
        """
        Returns the dividends distribution score address
        :return: Address of the dividends distribution score
        :rtype: :class:`iconservice.base.address.Address`
        """
        return self._dividends_score.get()

    @external
    def set_game_score(self, _score: Address) -> None:
        """
        Sets the roulette score address
        :param _score: Address of the roulette score
        :type _score: :class:`iconservice.base.address.Address`
        :return:
        """
        if self.msg.sender == self.owner:
            self._game_score.set(_score)

    @external(readonly=True)
    def get_game_score(self) -> Address:
        """
        Returns the roulette score address
        :return: Address of the roulette score
        :rtype: :class:`iconservice.base.address.Address`
        """
        return self._game_score.get()

    @external(readonly=True)
    def rewards_dist_complete(self) -> bool:
        """
        Checks the status for tap token distribution
        :return: True if tap token has been distributed for previous day
        :rtype: bool
        """
        return self._dist_complete.get()

    @external(readonly=True)
    def get_todays_total_wagers(self) -> int:
        """
        Provides total wagers made in current day.
        :return: Total wagers made in current day in loop
        :rtype: int
        """
        return self._daily_totals[self._day_index.get()].get()

    @external(readonly=True)
    def get_daily_wagers(self, _player: str) -> int:
        """
        Returns total wagers made by the player in the current day
        :param _player: Player address for which the wagers has to be checked
        :type _player: str
        :return: Wagers made by the player in current day
        :rtype: int
        """
        return self._wagers[self._day_index.get()][_player]

    @external(readonly=True)
    def get_expected_rewards(self, _player: str) -> int:
        """
        Returns the expected TAP tokens the player will receive according to the total wagers at that moment
        :param _player: Player address for which expected rewards is to be checked
        :type _player: str
        :return: Expected TAP tokens that the player can receive
        :rtype: int
        """
        total = self.get_todays_total_wagers()
        if total == 0:
            return 0
        expected_rewards = (self.get_todays_tap_distribution() * self.get_daily_wagers(_player) // total)
        return expected_rewards

    @external(readonly=True)
    def get_todays_tap_distribution(self) -> int:
        """
        Returns the amount of TAP to be distributed today
        :return:
        """
        token_score = self.create_interface_score(self._token_score.get(), TokenInterface)
        remaining_tokens = token_score.balanceOf(self.address)
        if remaining_tokens == 264000000 * TAP:
            return 2 * DAILY_TOKEN_DISTRIBUTION + remaining_tokens % DAILY_TOKEN_DISTRIBUTION
        elif remaining_tokens >= 251000000 * TAP:
            return DAILY_TOKEN_DISTRIBUTION + remaining_tokens % DAILY_TOKEN_DISTRIBUTION
        else:
            daily_dist = max(25000 * TAP, (self._yesterdays_tap_distribution.get() * 995) // 1000)
            daily_dist = min(daily_dist, remaining_tokens)
            return daily_dist

    @external
    def untether(self) -> None:
        """
        A function to redefine the value of self.owner once it is possible.
        To be included through an update if it is added to IconService.

        Sets the value of self.owner to the score holding the game treasury.
        """
        if self.tx.origin != self.owner:
            revert(f'Only the owner can call the untether method.')
        pass

    @external(readonly=True)
    def get_daily_wager_totals(self) -> str:
        """
        Returns all the addresses which have played games today and yesterday with their wagered amount in the entire
        platform
        :return: JSON data of yesterday's and today's players and their wagers
        :rtype: str
        """
        Logger.debug(f'{self.msg.sender} is getting daily wagers.', TAG)
        today = {}
        index = self._day_index.get()
        for address in self._addresses[index]:
            Logger.debug(f'Wager amount of {self._wagers[index][address]} being added.', TAG)
            today[address] = self._wagers[index][address]
        yesterday = {}
        index = (self._day_index.get() + 1) % 2
        for address in self._addresses[index]:
            Logger.debug(f'Wager amount of {self._wagers[index][address]} being added.', TAG)
            yesterday[address] = self._wagers[index][address]
        daily_wagers = {"today": today, "yesterday": yesterday}
        Logger.debug(f'Wager totals {daily_wagers}.', TAG)
        return json_dumps(daily_wagers)

    @external
    def accumulate_wagers(self, player: str, wager: int, day_index: int) -> None:
        """
        Records data of wagers made by players in any games in the ICONbet platform. If the day has changed then
        data for the index of today is cleared. Index can be 0 or 1. The wagerers from previous day are made eligible to
        receive TAP tokens. Calls the distribute function of dividends distribution score and distribute function for
        TAP tokens distribution if they are not completed.
        :param player: Address of the player playing any games in ICONbet platform
        :type player: str
        :param wager: Wager amount of the player
        :type wager: int
        :param day_index: Day index for which player data is to be recorded(0 or 1)
        :type day_index: int
        :return:
        """
        if self.msg.sender != self._game_score.get():
            revert(f'This function can only be called from the game score.')
        Logger.debug(f'In accumulate_wagers, day_index = {day_index}.', TAG)
        day = self._day_index.get()
        Logger.debug(f'self._day_index = {day}.', TAG)
        if day != day_index:
            Logger.debug(f'Setting self._day_index to {day_index}.', TAG)
            self._day_index.set(day_index)
            for _ in range(len(self._addresses[day_index])):
                self._wagers[day_index].remove(self._addresses[day_index].pop())
            if not self._rewards_gone.get():
                token_score = self.create_interface_score(self._token_score.get(), TokenInterface)
                remaining_tokens = token_score.balanceOf(self.address)
                if remaining_tokens == 0:
                    self._rewards_gone.set(True)
                else:
                    self._set_batch_size()
                    self._dist_index.set(0)
                    self._dist_complete.set(False)
                    self._wager_total.set(self._daily_totals[day].get())
                    self._set_daily_dist(remaining_tokens)
            self._daily_totals[day_index].set(0)
        Logger.debug(f'Lengths: {len(self._addresses[0])}, {len(self._addresses[1])}', TAG)
        Logger.debug(f'Adding wager from {player}.', TAG)
        self._daily_totals[day_index].set(self._daily_totals[day_index].get() + wager)
        Logger.debug(f'Total wagers = {self._daily_totals[day_index].get()}.', TAG)
        if player in self._addresses[day_index]:
            Logger.debug(f'Adding wager to {player} in _addresses[{day_index}].', TAG)
            self._wagers[day_index][player] += wager
        else:
            Logger.debug(f'Putting {player} in _addresses[{day_index}].', TAG)
            self._addresses[day_index].put(player)
            self._wagers[day_index][player] = wager

        dividends_score = self.create_interface_score(self._dividends_score.get(), DividendsInterface)

        if dividends_score.distribute():
            self._distribute()
        Logger.debug(f'Done in accumulate_wagers.'
                     f' self._day_index = {self._day_index.get()}.', TAG)

    def _set_batch_size(self) -> None:
        """
        Sets the batch size to be used for TAP distribution. Uses the function from roulette score
        :return:
        """
        game_score = self.create_interface_score(self._game_score.get(), GameInterface)
        size = game_score.get_batch_size(len(self._addresses[self._day_index.get()]))
        self._batch_size.set(size)

    def _distribute(self):
        """
        Main distribution function to distribute the TAP token to the wagerers. Distributes the TAP token only if this
        contract holds some TAP token.
        :return:
        """
        if self._rewards_gone.get():
            self._dist_complete.set(True)
            return
        Logger.debug(f'Beginning rewards distribution.', TAG)
        index = (self._day_index.get() + 1) % 2
        count = self._batch_size.get()
        addresses = self._addresses[index]
        length = len(addresses)
        start = self._dist_index.get()
        remaining_addresses = length - start
        if count > remaining_addresses:
            count = remaining_addresses
        end = start + count
        Logger.debug(f'Length of address list: {length}. Remaining = {remaining_addresses}', TAG)
        token_score = self.create_interface_score(self._token_score.get(), TokenInterface)
        total_dist = self._daily_dist.get()
        total_wagers = self._wager_total.get()
        if total_wagers == 0:
            self._dist_index.set(0)
            self._dist_complete.set(True)
            return
        for i in range(start, end):
            wagered = self._wagers[index][addresses[i]]
            rewards_due = total_dist * wagered // total_wagers
            total_dist -= rewards_due
            total_wagers -= wagered
            Logger.debug(f'Rewards due to {addresses[i]} = {rewards_due}', TAG)
            try:
                Logger.debug(f'Trying to send to ({addresses[i]}): {rewards_due}.', TAG)
                full_address = self.address.from_string(addresses[i])
                token_score.transfer(full_address, rewards_due)
                self.TokenTransfer(full_address, rewards_due)
                Logger.debug(f'Sent player ({addresses[i]}) {rewards_due}.', TAG)
            except BaseException as e:
                Logger.debug(f'Send failed. Exception: {e}', TAG)
                revert('Network problem. Rewards not sent. Will try again later. '
                       f'Exception: {e}')
        self._daily_dist.set(total_dist)
        self._wager_total.set(total_wagers)
        if end == length:
            self._dist_index.set(0)
            self._dist_complete.set(True)
        else:
            self._dist_index.set(self._dist_index.get() + count)

    def _set_daily_dist(self, remaining_tokens: int) -> None:
        """
        Sets the amount of TAP to be distributed on each day
        :param remaining_tokens: Remaining TAP tokens on the rewards contract
        :return:
        """
        if remaining_tokens == 264000000 * TAP:
            self._daily_dist.set(2 * DAILY_TOKEN_DISTRIBUTION + remaining_tokens % DAILY_TOKEN_DISTRIBUTION)
            self._yesterdays_tap_distribution.set(DAILY_TOKEN_DISTRIBUTION)
        elif remaining_tokens >= 251000000 * TAP:
            self._daily_dist.set(DAILY_TOKEN_DISTRIBUTION + remaining_tokens % DAILY_TOKEN_DISTRIBUTION)
            self._yesterdays_tap_distribution.set(DAILY_TOKEN_DISTRIBUTION)
        else:
            daily_dist = max(25000 * TAP, (self._yesterdays_tap_distribution.get() * 995) // 1000)
            daily_dist = min(daily_dist, remaining_tokens)
            self._yesterdays_tap_distribution.set(daily_dist)
            self._daily_dist.set(daily_dist)

    @payable
    def fallback(self):
        revert("This contract doesn't accept ICX")

    @external
    def tokenFallback(self, _from: Address, _value: int, _data: bytes):
        """This score will hold the 80% of TAP tokens for distribution."""
        token_score = self.create_interface_score(self._token_score.get(), TokenInterface)
        if token_score.balanceOf(self.address) == 264000000 * TAP:
            revert("Not able to receive further TAP when the balance is 264M tap tokens")
        if token_score.symbol() != 'TAP':
            revert(f'The Rewards Score can only receive TAP tokens.')
        self._rewards_gone.set(False)
        Logger.debug(f'({_value}) TAP tokens received from {_from}.', TAG)
