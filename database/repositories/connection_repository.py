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
    
    def get_by_id(self, connection_id: int) -> Optional[Dict]:
        """Получить подключение по ID"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Получаем основную информацию
            cursor.execute("""
                SELECT id, connection_type, address, router_model, port, fiber_meters, 
                       snr_box_model, twisted_pair_meters, created_at, created_by, router_quantity, 
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
            
            query = f"""
                SELECT 
                    c.id,
                    c.connection_type,
                    c.address,
                    c.router_model,
                    c.snr_box_model,
                    c.port,
                    c.fiber_meters,
                    c.twisted_pair_meters,
                    c.created_at,
                    COUNT(DISTINCT ce_all.employee_id) as employee_count
                FROM connections c
                JOIN connection_employees ce_target 
                    ON ce_target.connection_id = c.id AND ce_target.employee_id = ?
                JOIN connection_employees ce_all 
                    ON ce_all.connection_id = c.id
                WHERE 1=1
                {date_condition}
                GROUP BY c.id
                ORDER BY c.created_at DESC
            """
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            connection_ids = [row['id'] for row in rows]
            employees_map: Dict[int, List[str]] = {}
            movement_map: Dict[int, Dict[str, Dict[str, float]]] = {}

            if connection_ids:
                placeholders = ",".join("?" for _ in connection_ids)
                cursor.execute(f"""
                    SELECT ce.connection_id, e.full_name
                    FROM connection_employees ce
                    JOIN employees e ON e.id = ce.employee_id
                    WHERE ce.connection_id IN ({placeholders})
                    ORDER BY ce.connection_id, e.full_name
                """, connection_ids)
                
                for emp_row in cursor.fetchall():
                    employees_map.setdefault(emp_row['connection_id'], []).append(emp_row['full_name'])

                # Агрегируем списанное оборудование по подключению
                cursor.execute(
                    f"""
                        SELECT connection_id, item_type, item_name, SUM(quantity) as qty
                        FROM material_movement_log
                        WHERE connection_id IN ({placeholders})
                          AND item_type IN ('onu', 'media_converter', 'snr_box')
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
                emp_count = max(conn_dict['employee_count'], 1)
                
                conn_dict['employee_fiber_meters'] = round(conn_dict['fiber_meters'] / emp_count, 2)
                conn_dict['employee_twisted_pair_meters'] = round(conn_dict['twisted_pair_meters'] / emp_count, 2)
                conn_dict['all_employees'] = employees_map.get(conn_dict['id'], [])
                conn_dict['total_fiber_meters'] = conn_dict['fiber_meters']
                conn_dict['total_twisted_pair_meters'] = conn_dict['twisted_pair_meters']

                mov = movement_map.get(conn_dict['id'], {})
                conn_dict['snr_spent'] = _format_items(mov.get('snr_box', {})) if mov.get('snr_box') else (conn_dict.get('snr_box_model') or "-")
                conn_dict['onu_spent'] = _format_items(mov.get('onu', {}))
                conn_dict['media_spent'] = _format_items(mov.get('media_converter', {}))
                
                connections.append(conn_dict)
                total_fiber_share += conn_dict['employee_fiber_meters']
                total_twisted_share += conn_dict['employee_twisted_pair_meters']
                total_fiber_all += conn_dict['total_fiber_meters']
                total_twisted_all += conn_dict['total_twisted_pair_meters']
            
            conn.close()
            
            stats = {
                'total_connections': len(connections),
                'total_fiber_meters': round(total_fiber_share, 2),
                'total_twisted_pair_meters': round(total_twisted_share, 2),
                'total_connection_fiber_meters': round(total_fiber_all, 2),
                'total_connection_twisted_pair_meters': round(total_twisted_all, 2),
            }
            
            return connections, stats
        except Exception as e:
            logger.error(f"Ошибка при получении отчета по сотруднику: {e}")
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
                    c.snr_box_model,
                    c.port,
                    c.fiber_meters,
                    c.twisted_pair_meters,
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
                          AND item_type IN ('onu', 'media_converter', 'snr_box')
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
                conn_dict["all_employees"] = employees_map.get(conn_dict["id"], [])
                conn_dict["total_fiber_meters"] = conn_dict["fiber_meters"]
                conn_dict["total_twisted_pair_meters"] = conn_dict["twisted_pair_meters"]

                mov = movement_map.get(conn_dict["id"], {})
                conn_dict["snr_spent"] = _format_items(mov.get("snr_box", {})) if mov.get("snr_box") else (conn_dict.get("snr_box_model") or "-")
                conn_dict["onu_spent"] = _format_items(mov.get("onu", {}))
                conn_dict["media_spent"] = _format_items(mov.get("media_converter", {}))

                connections.append(conn_dict)
                total_fiber_share += conn_dict["employee_fiber_meters"]
                total_twisted_share += conn_dict["employee_twisted_pair_meters"]
                total_fiber_all += conn_dict["fiber_meters"]
                total_twisted_all += conn_dict["twisted_pair_meters"]

            stats = {
                "total_connections": len(connections),
                "total_fiber_meters": round(total_fiber_share, 2),
                "total_twisted_pair_meters": round(total_twisted_share, 2),
                "total_connection_fiber_meters": round(total_fiber_all, 2),
                "total_connection_twisted_pair_meters": round(total_twisted_all, 2),
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
