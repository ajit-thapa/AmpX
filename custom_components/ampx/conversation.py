"""AmpX's own assistant, answered by the AI gateway (only when a gateway URL is set)."""

from __future__ import annotations

import logging
from typing import Literal

from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import llm
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_GW_LLM_API, CONF_GW_MODEL, CONF_GW_PROMPT, CONF_GW_STREAM, CONF_GW_TEMPERATURE, DOMAIN
from .gateway_llm import async_run_chat_log

LOGGER = logging.getLogger(__name__)
from .gateway_entity import GatewayEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    brain = hass.data[DOMAIN][entry.entry_id]
    if brain.gateway is not None:
        async_add_entities([AmpXAssistant(brain)])


class AmpXAssistant(GatewayEntity, conversation.ConversationEntity):
    """Assist agent on the gateway; controls the home through Assist and AmpX's own tools."""

    _attr_translation_key = "assistant"
    _key = "assistant"

    def __init__(self, brain) -> None:
        super().__init__(brain)
        if brain.opts.get(CONF_GW_LLM_API):
            self._attr_supported_features = conversation.ConversationEntityFeature.CONTROL

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        return MATCH_ALL

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.brain.gateway_agent = self.entity_id

    async def _usable_apis(self, llm_context: llm.LLMContext, api_ids: list[str]) -> list[str]:
        """Tool APIs this caller may use. HA's `homeassistant` API, for one, refuses non-admin
        callers, and AmpX's own calls have no user: drop such an API for this call, keep the rest."""
        usable = []
        for api_id in api_ids:
            try:
                await llm.async_get_api(self.hass, api_id, llm_context)
            except HomeAssistantError as err:
                LOGGER.debug("Leaving out tool API %s for this call: %s", api_id, err or type(err).__name__)
                continue
            usable.append(api_id)
        return usable

    async def _async_handle_message(self, user_input: conversation.ConversationInput, chat_log: conversation.ChatLog) -> conversation.ConversationResult:
        opts = self.brain.opts
        llm_context = user_input.as_llm_context(DOMAIN)
        try:
            await chat_log.async_provide_llm_data(
                llm_context,
                await self._usable_apis(llm_context, opts.get(CONF_GW_LLM_API) or []) or None,
                opts.get(CONF_GW_PROMPT) or None,
                user_input.extra_system_prompt,
            )
        except conversation.ConverseError as err:
            return err.as_conversation_result()
        await async_run_chat_log(
            self.hass, self.brain.gateway, self.entity_id, chat_log,
            model=opts.get(CONF_GW_MODEL) or "auto",
            stream=bool(opts.get(CONF_GW_STREAM, True)),
            temperature=opts.get(CONF_GW_TEMPERATURE),
        )
        return conversation.async_get_result_from_chat_log(user_input, chat_log)
