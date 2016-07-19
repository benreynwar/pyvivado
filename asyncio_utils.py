class FakeGatheredFuture():

    def __init__(self, futures):
        self.futures = futures

    def done(self):
        return all([f.done() for f in self.futures])

    def result(self):
        if not self.done():
            raise Exception('Result not ready')
        else:
            result = [f.result() for f in self.futures]
        return result


def gather(*futures):
    return FakeGatheredFuture(futures)
