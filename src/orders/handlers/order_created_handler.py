"""
Handler: Order Created
SPDX-License-Identifier: LGPL-3.0-or-later
Auteurs : Gabriel C. Ullmann, Fabio Petrillo, 2025
"""
from typing import Dict, Any
import config
from db import get_sqlalchemy_session
from event_management.base_handler import EventHandler
from orders.commands.order_event_producer import OrderEventProducer
from stocks.commands.write_stock import check_out_items_from_stock


class OrderCreatedHandler(EventHandler):
    """Handles OrderCreated events"""
    
    def __init__(self):
        self.order_producer = OrderEventProducer()
        super().__init__()
    
    def get_event_type(self) -> str:
        """Get event type name"""
        return "OrderCreated"

    def handle(self, event_data: Dict[str, Any]) -> None:
        """Exécuté chaque fois que l'événement OrderCreated est publié"""
        order_event_producer = OrderEventProducer()
        session = get_sqlalchemy_session()

        try:
            # La création de la commande a réussi, alors déclenchez la mise à jour du stock
            # On utilise les items contenus dans les données de l'événement
            check_out_items_from_stock(session, event_data['order_items'])
            session.commit()

            # Si la mise à jour du stock a réussi, on passe à l'état suivant
            event_data['event'] = "StockDecreased"
            self.logger.debug(f"Stock diminué avec succès pour la commande {event_data.get('order_id')}")

        except Exception as e:
            # En cas d'erreur (ex: stock insuffisant), on annule la transaction DB
            session.rollback()

            # On déclenche l'événement d'échec pour informer la saga
            event_data['event'] = "StockDecreaseFailed"
            event_data['error'] = str(e)
            self.logger.error(f"Échec de diminution du stock : {str(e)}")

        finally:
            # On ferme la session et on publie l'événement (succès ou échec) dans Kafka
            session.close()
            order_event_producer.get_instance().send(config.KAFKA_TOPIC, value=event_data)


    def _handle_implemented(self, event_data: Dict[str, Any]) -> None:
        """
        This method is here as a reference for the implementation of the method handle.
        It will never be called if Sotre Manager is following normal operation.
        Once you copy-paste the implementation, you can delete this method if you want.
        """
        order_event_producer = OrderEventProducer()
        try:
            # La création de la comande a réussi, alors déclenchez la mise à jour du stock.
            session = get_sqlalchemy_session()
            check_out_items_from_stock(session, event_data['order_items'])
            session.commit()
            # Si la mise à jour du stock a réussi, déclenchez StockDecreased.
            event_data['event'] = "StockDecreased"
        except Exception as e:
            session.rollback()
            # Si la mise à jour du stock a échoué, déclenchez StockDecreaseFailed.
            event_data['event'] = "StockDecreaseFailed"
            event_data['error'] = str(e)
        finally:
            session.close()
            order_event_producer.get_instance().send(config.KAFKA_TOPIC, value=event_data)


