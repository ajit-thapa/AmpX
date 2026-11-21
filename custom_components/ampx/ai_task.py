"""AmpX's AI Task entity on the gateway: camera looks and structured data."""

from __future__ import annotations

from homeassistant.components import ai_task, conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_GW_MODEL, CONF_GW_STRUCTURED, CONF_GW_TASK_MODEL, CONF_GW_TEMPERATURE, DOMAIN
from .gateway_entity import GatewayEntity
from .gateway_llm import async_run_chat_log, parse_json_reply


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    brain = hass.data[DOMAIN][entry.entry_id]
    if brain.gateway is not None:
        async_add_entities([AmpXAITask(brain)])


class AmpXAITask(GatewayEntity, ai_task.AITaskEntity):
    """Runs ai_task.generate_data on the gateway."""

    _attr_translation_key = "ai_task"
    _key = "ai_task"
    _attr_supported_features = ai_task.AITaskEntityFeature.GENERATE_DATA | ai_task.AITaskEntityFeature.SUPPORT_ATTACHMENTS

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.brain.gateway_task = self.entity_id

    async def _async_generate_data(self, task: ai_task.GenDataTask, chat_log: conversation.ChatLog) -> ai_task.GenDataTaskResult:
        opts = self.brain.opts
        await async_run_chat_log(
            self.hass, self.brain.gateway, self.entity_id, chat_log,
            model=opts.get(CONF_GW_TASK_MODEL) or opts.get(CONF_GW_MODEL) or "auto",
            stream=False,
            temperature=opts.get(CONF_GW_TEMPERATURE),
            structured=opts.get(CONF_GW_STRUCTURED) or "auto",
            structure_name=task.name,
            structure=task.structure,
        )
        last = chat_log.content[-1]
        if not isinstance(last, conversation.AssistantContent):
            raise HomeAssistantError("The model gave no answer")
        text = last.content or ""
        if not task.structure:
            return ai_task.GenDataTaskResult(conversation_id=chat_log.conversation_id, data=text)
        try:
            data = parse_json_reply(text)
        except ValueError as err:
            raise HomeAssistantError(f"The model did not return valid JSON: {text[:200]}") from err
        return ai_task.GenDataTaskResult(conversation_id=chat_log.conversation_id, data=data)
