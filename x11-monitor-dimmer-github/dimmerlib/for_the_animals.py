from __future__ import annotations


class ForTheAnimals:
    CONFIG_KEY = "for_the_animals"
    STATE_VERSION = "v0.50-production-1"

    DEFAULT_MESSAGE = (
        "If this tool has been useful, please consider showing appreciation "
        "by donating to a local animal shelter or cruelty prevention service."
    )

    def __init__(self, config: dict):
        self.config = config
        self.state = self.config.setdefault(self.CONFIG_KEY, {})

        # Production profile:
        # - first prompt on open 100
        # - remind later = +10 opens
        # - no thanks = +200 opens
        if self.state.get("state_version") != self.STATE_VERSION:
            self.state.clear()
            self.state.update(
                {
                    "state_version": self.STATE_VERSION,
                    "enabled": True,
                    "launch_count": 0,
                    "next_prompt_at": 100,
                    "remind_later_step": 10,
                    "no_thanks_step": 200,
                    "message": self.DEFAULT_MESSAGE,
                }
            )

    def is_enabled(self) -> bool:
        return bool(self.state.get("enabled", True))

    def get_launch_count(self) -> int:
        try:
            return max(0, int(self.state.get("launch_count", 0)))
        except Exception:
            return 0

    def get_next_prompt_at(self) -> int:
        try:
            return max(1, int(self.state.get("next_prompt_at", 100)))
        except Exception:
            return 100

    def get_remind_later_step(self) -> int:
        try:
            return max(1, int(self.state.get("remind_later_step", 10)))
        except Exception:
            return 10

    def get_no_thanks_step(self) -> int:
        try:
            return max(1, int(self.state.get("no_thanks_step", 200)))
        except Exception:
            return 200

    def get_message(self) -> str:
        msg = str(self.state.get("message", self.DEFAULT_MESSAGE)).strip()
        return msg or self.DEFAULT_MESSAGE

    def should_show(self) -> bool:
        if not self.is_enabled():
            return False
        return self.get_launch_count() >= self.get_next_prompt_at()

    def controller_opened(self) -> bool:
        self.state["launch_count"] = self.get_launch_count() + 1
        return self.should_show()

    def remind_me_later(self) -> None:
        self.state["next_prompt_at"] = self.get_launch_count() + self.get_remind_later_step()

    def no_thanks(self) -> None:
        self.state["next_prompt_at"] = self.get_launch_count() + self.get_no_thanks_step()

    def export_debug_state(self) -> dict:
        return {
            "state_version": self.state.get("state_version"),
            "enabled": self.is_enabled(),
            "launch_count": self.get_launch_count(),
            "next_prompt_at": self.get_next_prompt_at(),
            "remind_later_step": self.get_remind_later_step(),
            "no_thanks_step": self.get_no_thanks_step(),
            "message": self.get_message(),
            "should_show": self.should_show(),
        }
