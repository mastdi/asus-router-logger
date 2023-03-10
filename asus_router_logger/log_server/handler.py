#  Copyright (c) 2023. Martin Storgaard Dieu <martin@storgaarddieu.com>
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
import typing

import pyzabbix

import asus_router_logger.domain as domain
import asus_router_logger.hooks.zabbix
import asus_router_logger.preprocessors.dnsmasq_dhcp as dnsmasq_dhcp_preprocessor
import asus_router_logger.preprocessors.wlc as wlc_preprocessor
import asus_router_logger.settings
import asus_router_logger.util.logging as logging
import asus_router_logger.util.rfc3164_parser


class LogHandler:
    def __init__(self):
        settings = asus_router_logger.settings.settings()
        zabbix_servers = settings.zabbix_servers
        sender = pyzabbix.ZabbixSender(
            zabbix_server=zabbix_servers[0][0], zabbix_port=zabbix_servers[0][1]
        )
        self.zabbix_trapper = asus_router_logger.hooks.zabbix.ZabbixTrapper(sender)
        logging.logger.info("Log handler is ready")

    async def handle(self, packet: bytes, host: str, port: int) -> None:
        # The packet is a single log entry encoded in ascii according to RFC3164
        entry = packet.decode("ascii")
        logging.echo_logger.debug(entry.strip())

        # Parse the log record
        record = asus_router_logger.util.rfc3164_parser.parse(entry)

        # Pre-process the record
        message: typing.Optional[domain.Message]
        if record.process == "wlceventd":
            message = wlc_preprocessor.preprocess_wireless_lan_controller_event(record)
        elif record.process == "dnsmasq-dhcp":
            message = dnsmasq_dhcp_preprocessor.preprocess_dnsmasq_dhcp_event(record)
        else:
            # Only preprocessors for logs with a named process is supported
            return

        # Act if needed
        if message is not None:
            await self.zabbix_trapper.send(record, message)
