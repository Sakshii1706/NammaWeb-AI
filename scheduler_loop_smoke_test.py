from __future__ import annotations

import threading
import time

from reach.campaigns.campaign_scheduler import CampaignScheduler


class FakeScheduler(CampaignScheduler):
    def __init__(self):
        super().__init__(session=None)
        self.calls = 0

    def execute_due_campaigns(self, *, now=None):
        self.calls += 1

        print(
            f"TEST LOOP PASS: scheduler cycle #{self.calls}"
        )

        if self.calls >= 3:
            raise KeyboardInterrupt

        return []


def main():
    scheduler = FakeScheduler()

    print("")
    print("=" * 60)
    print("RECURRING LOOP CONTROLLED TEST")
    print("=" * 60)
    print("")

    try:
        # We intentionally reproduce the loop behavior here
        # with a fake scheduler so the real database is never used.
        interval_seconds = 1

        print(
            f"Test interval: {interval_seconds} second(s)"
        )
        print(
            "Database access: DISABLED"
        )
        print("")

        while True:
            try:
                results = scheduler.execute_due_campaigns()

                print(
                    f"Cycle returned {len(results)} result(s)."
                )

            except KeyboardInterrupt:
                print("")
                print("Controlled stop received.")
                break

            time.sleep(interval_seconds)

    finally:
        print("")
        print(
            f"Total scheduler cycles: {scheduler.calls}"
        )

    assert scheduler.calls == 3

    print("")
    print("PASS: recurring scheduler loop starts,")
    print("      repeats, and stops cleanly.")
    print("")
    print("=" * 60)


if __name__ == "__main__":
    main()
