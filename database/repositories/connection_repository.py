"""
Репозиторий для работы с подключениями
"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging

from database.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class ConnectionRepository(BaseRepository):
    """Репозиторий для управления подключениями"""
    
    def create(
        self,
        connection_type: str,
        address: str,
        router_model: str,
        port: str,
        fiber_meters: float,
        twisted_pair_meters: float,
        created_by: int,
        router_quantity: int = 1,
        contract_signed: bool = False,
        router_access: bool = False,
        telegram_bot_connected: bool = False
    ) -> Optional[int]:
        """Создать новое подключение"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Создаем запись подключения
            cursor.execute("""
                INSERT INTO connections 
                (connection_type, address, router_model, port, fiber_meters, 
                 twisted_pair_meters, created_by, router_quantity, contract_signed, 
                 router_access, telegram_bot_connected)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                connection_type, address, router_model, port, fiber_meters,
                twisted_pair_meters, created_by, router_quantity,
                1 if contract_signed else 0,
                1 if router_access else 0,
                1 if telegram_bot_connected else 0
            ))
            
            connection_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            logger.info(f"Создано подключение ID: {connection_id}")
            return connection_id
        except Exception as e:
            logger.error(f"Ошибка при создании подключения: {e}")
            return None
    
    def link_employees(self, connection_id: int, employee_ids: List[int]) -> bool:
        """Связать сотрудников с подключением"""
        try:
            params_list = [(connection_id, emp_id) for emp_id in employee_ids]
            return self.execute_many("""
                INSERT INTO connection_employees (connection_id, employee_id)
                VALUES (?, ?)
            """, params_list)
        except Exception as e:
            logger.error(f"Ошибка при связывании сотрудников: {e}")
            return False
    
    def save_photos(self, connection_id: int, photo_file_ids: List[str]) -> bool:
        """Сохранить фотографии подключения"""
        try:
            params_list = [
                (connection_id, photo_id, 'general', idx)
                for idx, photo_id in enumerate(photo_file_ids)
            ]
            return self.execute_many("""
                INSERT INTO connection_photos (connection_id, photo_file_id, photo_category, photo_order)
                VALUES (?, ?, ?, ?)
            """, params_list)
        except Exception as e:
            logger.error(f"Ошибка при сохранении фотографий: {e}")
            return False
    
    def get_by_id(self, connection_id: int) -> Optional[Dict]:
        """Получить подключение по ID"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Получаем основную информацию
            cursor.execute("""
                SELECT id, connection_type, address, router_model, port, fiber_meters, 
                       twisted_pair_meters, created_at, created_by, router_quantity, 
                       contract_signed, router_access, telegram_bot_connected
                FROM connections
                WHERE id = ?
            """, (connection_id,))
            
            row = cursor.fetchone()
            if not row:
                conn.close()
                return None
            
            connection = dict(row)
            
            # Получаем сотрудников
            cursor.execute("""
                SELECT e.id, e.full_name
                FROM employees e
                JOIN connection_employees ce ON e.id = ce.employee_id
                WHERE ce.connection_id = ?
                ORDER BY e.full_name
            """, (connection_id,))
            connection['employees'] = [dict(row) for row in cursor.fetchall()]
            
            # Получаем фотографии
            cursor.execute("""
                SELECT photo_file_id
                FROM connection_photos
                WHERE connection_id = ?
                ORDER BY photo_order
            """, (connection_id,))
            connection['photos'] = [row['photo_file_id'] for row in cursor.fetchall()]
            
            conn.close()
            return connection
        except Exception as e:
            logger.error(f"Ошибка при получении подключения: {e}")
            return None
    
    def get_employee_report(
        self,
        employee_id: int,
        days: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> tuple[List[Dict], Dict]:
        """Получить отчет по сотруднику за период"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Формируем условие по дате
            date_condition = ""
            params = [employee_id]
            if start_date and end_date:
                date_condition = "AND c.created_at BETWEEN ? AND ?"
                params.append(start_date.strftime("%Y-%m-%d %H:%M:%S"))
                params.append(end_date.strftime("%Y-%m-%d %H:%M:%S"))
            elif start_date:
                date_condition = "AND c.created_at >= ?"
                params.append(start_date.strftime("%Y-%m-%d %H:%M:%S"))
            elif days is not None:
                date_limit = datetime.now() - timedelta(days=days)
                date_condition = "AND c.created_at >= ?"
                params.append(date_limit.strftime("%Y-%m-%d %H:%M:%S"))
            
            # Получаем подключения с участием сотрудника
            query = f"""
                SELECT 
                    c.id,
                    c.connection_type,
                    c.address,
                    c.router_model,
                    c.port,
                    c.fiber_meters,
                    c.twisted_pair_meters,
                    c.created_at,
                    COUNT(DISTINCT ce.employee_id) as employee_count
                FROM connections c
                JOIN connection_employees ce ON c.id = ce.connection_id
                WHERE ce.connection_id IN (
                    SELECT connection_id 
                    FROM connection_employees 
                    WHERE employee_id = ?
                )
                {date_condition}
                GROUP BY c.id
                ORDER BY c.created_at DESC
            """
            
            cursor.execute(query, params)
            connections = []
            
            total_fiber = 0.0
            total_twisted = 0.0
            
            for row in cursor.fetchall():
                conn_dict = dict(row)
                emp_count = conn_dict['employee_count']
                
                # Рассчитываем долю для сотрудника
                conn_dict['employee_fiber_meters'] = round(conn_dict['fiber_meters'] / emp_count, 2)
                conn_dict['employee_twisted_pair_meters'] = round(conn_dict['twisted_pair_meters'] / emp_count, 2)
                
                # Получаем список всех исполнителей для этого подключения
                cursor.execute("""
                    SELECT e.full_name
                    FROM employees e
                    JOIN connection_employees ce ON e.id = ce.employee_id
                    WHERE ce.connection_id = ?
                    ORDER BY e.full_name
                """, (conn_dict['id'],))
                conn_dict['all_employees'] = [row['full_name'] for row in cursor.fetchall()]
                
                connections.append(conn_dict)
                total_fiber += conn_dict['employee_fiber_meters']
                total_twisted += conn_dict['employee_twisted_pair_meters']
            
            conn.close()
            
            stats = {
                'total_connections': len(connections),
                'total_fiber_meters': round(total_fiber, 2),
                'total_twisted_pair_meters': round(total_twisted, 2)
            }
            
            return connections, stats
        except Exception as e:
            logger.error(f"Ошибка при получении отчета: {e}")
            return [], {}
    def get_global_report(
        self,
        days: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> tuple[List[Dict], Dict]:
        """Получить общий отчет по всем сотрудникам за период"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            date_condition = ""
            params: list = []
            if start_date and end_date:
                date_condition = "WHERE c.created_at BETWEEN ? AND ?"
                params.append(start_date.strftime("%Y-%m-%d %H:%M:%S"))
                params.append(end_date.strftime("%Y-%m-%d %H:%M:%S"))
            elif start_date:
                date_condition = "WHERE c.created_at >= ?"
                params.append(start_date.strftime("%Y-%m-%d %H:%M:%S"))
            elif days is not None:
                date_limit = datetime.now() - timedelta(days=days)
                date_condition = "WHERE c.created_at >= ?"
                params.append(date_limit.strftime("%Y-%m-%d %H:%M:%S"))

            query = f"""
                SELECT 
                    c.id,
                    c.connection_type,
                    c.address,
                    c.router_model,
                    c.router_quantity,
                    c.contract_signed,
                    c.router_access,
                    c.telegram_bot_connected,
                    c.snr_box_model,
                    c.snr_box_quantity,
                    c.comment,
                    c.port,
                    c.fiber_meters,
                    c.twisted_pair_meters,
                    c.onu_model,
                    c.onu_quantity,
                    c.media_converter_model,
                    c.media_converter_quantity,
                    c.sfp_module_model,
                    c.sfp_module_quantity,
                    c.hooks_quantity,
                    c.ork_quantity,
                    c.mufta_quantity,
                    c.created_at,
                    COUNT(DISTINCT ce.employee_id) as employee_count
                FROM connections c
                JOIN connection_employees ce ON ce.connection_id = c.id
                {date_condition}
                GROUP BY c.id
                ORDER BY c.created_at DESC
            """

            cursor.execute(query, params)
            rows = cursor.fetchall()

            connection_ids = [row["id"] for row in rows]
            employees_map: Dict[int, List[str]] = {}
            movement_map: Dict[int, Dict[str, Dict[str, float]]] = {}

            if connection_ids:
                placeholders = ",".join("?" for _ in connection_ids)
                cursor.execute(
                    f"""
                        SELECT ce.connection_id, e.full_name
                        FROM connection_employees ce
                        JOIN employees e ON e.id = ce.employee_id
                        WHERE ce.connection_id IN ({placeholders})
                        ORDER BY ce.connection_id, e.full_name
                    """,
                    connection_ids,
                )

                for emp_row in cursor.fetchall():
                    employees_map.setdefault(emp_row["connection_id"], []).append(emp_row["full_name"])

                cursor.execute(
                    f"""
                        SELECT connection_id, item_type, item_name, SUM(quantity) as qty
                        FROM material_movement_log
                        WHERE connection_id IN ({placeholders})
                          AND item_type IN ('onu', 'media_converter', 'snr_box', 'sfp_module')
                          AND operation_type = 'deduct'
                        GROUP BY connection_id, item_type, item_name
                    """,
                    connection_ids,
                )
                for mov in cursor.fetchall():
                    conn_mov = movement_map.setdefault(mov["connection_id"], {})
                    type_mov = conn_mov.setdefault(mov["item_type"], {})
                    type_mov[mov["item_name"]] = mov["qty"]

            connections = []
            total_fiber_share = 0.0
            total_twisted_share = 0.0
            total_fiber_all = 0.0
            total_twisted_all = 0.0
            total_hooks_all = 0.0
            total_ork_all = 0.0
            total_mufta_all = 0.0
            total_employee_hooks = 0.0
            total_employee_ork = 0.0
            total_employee_mufta = 0.0
            total_router_quantity = 0.0
            total_snr_quantity = 0.0
            total_onu_quantity = 0.0
            total_media_quantity = 0.0
            total_sfp_quantity = 0.0

            def _format_items(items: Dict[str, float]) -> str:
                if not items:
                    return "-"
                parts = []
                for name, qty in items.items():
                    qty_fmt = int(qty) if float(qty).is_integer() else round(qty, 2)
                    parts.append(f"{name} x{qty_fmt}")
                return "; ".join(parts)

            for row in rows:
                conn_dict = dict(row)
                emp_count = max(conn_dict["employee_count"], 1)

                conn_dict["employee_fiber_meters"] = round(conn_dict["fiber_meters"] / emp_count, 2)
                conn_dict["employee_twisted_pair_meters"] = round(conn_dict["twisted_pair_meters"] / emp_count, 2)
                hooks_total = float(conn_dict.get("hooks_quantity") or 0)
                ork_total = float(conn_dict.get("ork_quantity") or 0)
                mufta_total = float(conn_dict.get("mufta_quantity") or 0)
                router_raw_qty = float(conn_dict.get("router_quantity") or 0)

                conn_dict["employee_hooks"] = round(hooks_total / emp_count, 2) if hooks_total else 0.0
                conn_dict["employee_ork"] = round(ork_total / emp_count, 2) if ork_total else 0.0
                conn_dict["employee_mufta"] = round(mufta_total / emp_count, 2) if mufta_total else 0.0
                conn_dict["all_employees"] = employees_map.get(conn_dict["id"], [])
                conn_dict["total_fiber_meters"] = conn_dict["fiber_meters"]
                conn_dict["total_twisted_pair_meters"] = conn_dict["twisted_pair_meters"]

                mov = movement_map.get(conn_dict["id"], {})
                snr_mov = mov.get("snr_box", {})
                onu_mov = mov.get("onu", {})
                media_mov = mov.get("media_converter", {})
                sfp_mov = mov.get("sfp_module", {})

                conn_dict["snr_spent"] = _format_items(snr_mov) if snr_mov else (conn_dict.get("snr_box_model") or "-")
                conn_dict["onu_spent"] = _format_items(onu_mov)
                conn_dict["media_spent"] = _format_items(media_mov)
                conn_dict["sfp_spent"] = _format_items(sfp_mov)

                snr_qty = sum(float(qty or 0) for qty in snr_mov.values()) if snr_mov else float(conn_dict.get("snr_box_quantity") or 0)
                onu_qty = sum(float(qty or 0) for qty in onu_mov.values()) if onu_mov else float(conn_dict.get("onu_quantity") or 0)
                media_qty = sum(float(qty or 0) for qty in media_mov.values()) if media_mov else float(conn_dict.get("media_converter_quantity") or 0)
                sfp_qty = sum(float(qty or 0) for qty in sfp_mov.values()) if sfp_mov else float(conn_dict.get("sfp_module_quantity") or 0)
                has_router = bool(conn_dict.get("router_model")) and conn_dict["router_model"] not in ("-", None)
                router_qty = router_raw_qty if has_router and router_raw_qty else 0.0
                conn_dict["router_quantity"] = router_qty

                connections.append(conn_dict)
                total_fiber_share += conn_dict["employee_fiber_meters"]
                total_twisted_share += conn_dict["employee_twisted_pair_meters"]
                total_fiber_all += conn_dict["total_fiber_meters"]
                total_twisted_all += conn_dict["total_twisted_pair_meters"]
                total_hooks_all += hooks_total
                total_ork_all += ork_total
                total_mufta_all += mufta_total
                total_employee_hooks += conn_dict["employee_hooks"]
                total_employee_ork += conn_dict["employee_ork"]
                total_employee_mufta += conn_dict["employee_mufta"]
                total_router_quantity += router_qty
                total_snr_quantity += snr_qty
                total_onu_quantity += onu_qty
                total_media_quantity += media_qty
                total_sfp_quantity += sfp_qty

            conn.close()

            stats = {
                "total_connections": len(connections),
                "total_fiber_meters": round(total_fiber_share, 2),
                "total_twisted_pair_meters": round(total_twisted_share, 2),
                "total_connection_fiber_meters": round(total_fiber_all, 2),
                "total_connection_twisted_pair_meters": round(total_twisted_all, 2),
                "total_hooks_quantity": round(total_hooks_all, 2),
                "total_ork_quantity": round(total_ork_all, 2),
                "total_mufta_quantity": round(total_mufta_all, 2),
                "total_employee_hooks": round(total_employee_hooks, 2),
                "total_employee_ork": round(total_employee_ork, 2),
                "total_employee_mufta": round(total_employee_mufta, 2),
                "total_router_quantity": round(total_router_quantity, 2),
                "total_snr_quantity": round(total_snr_quantity, 2),
                "total_onu_quantity": round(total_onu_quantity, 2),
                "total_media_quantity": round(total_media_quantity, 2),
                "total_sfp_quantity": round(total_sfp_quantity, 2),
            }

            return connections, stats
        except Exception as exc:
            logger.error("Ошибка при получении общего отчета: %s", exc)
            return [], {"total_connections": 0, "total_fiber_meters": 0, "total_twisted_pair_meters": 0}
    
    def get_all_count(self) -> int:
        """Получить общее количество подключений"""
        try:
            result = self.execute_query(
                "SELECT COUNT(*) as count FROM connections",
                fetch_one=True
            )
            return result['count'] if result else 0
        except Exception as e:
            logger.error(f"Ошибка при подсчете подключений: {e}")
            return 0
