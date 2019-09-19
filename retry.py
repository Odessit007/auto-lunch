import logging
import time


def retry(n_tries=5, time_delta=10, exceptions=None):
    def _retry(fun):
        nonlocal exceptions
        if exceptions is None:
            exceptions = Exception

        def _fun(*args, **kwargs):
            for i in range(n_tries):
                logging.info(f'\tTrying to run {fun.__name__}, {i + 1}-th try')
                try:
                    result = fun(*args, **kwargs)
                    logging.info(f'\t{i+1}-th run succeeded for {fun.__name__}')
                    return result
                except exceptions:
                    logging.info(f'\t{i+1}-th run failed for {fun.__name__}. Falling asleep for {time_delta} seconds')
                    time.sleep(time_delta)
            else:
                logging.error(f'\tAll {n_tries} tries failed for {fun.__name__}')
                return None

        return _fun
    return _retry


if __name__ == '__main__':
    i = 0

    @retry(3, exceptions=(ZeroDivisionError, TypeError))
    def fun():
        global i
        y = 1
        if i < 2:
            y = 'a'
        print(i, y, flush=True)
        i += 1
        return 1 / y

    fun()
