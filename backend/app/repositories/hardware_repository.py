from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.speaker_node import SpeakerNode
from app.models.speaker_queue import SpeakerQueue
from app.schemas.hardware import SpeakerNodeCreate, SpeakerNodeUpdate, SpeakerNodeHeartbeat


def create_speaker_node(db: Session, node_in: SpeakerNodeCreate) -> SpeakerNode:
    node = SpeakerNode(
        name=node_in.name,
        mac_address=node_in.mac_address,
        ip_address=node_in.ip_address,
        department_id=node_in.department_id,
        zone=node_in.zone,
        volume=node_in.volume,
        status="ONLINE" if node_in.ip_address else "OFFLINE",
        last_heartbeat=datetime.now(timezone.utc).replace(tzinfo=None) if node_in.ip_address else None,
    )
    db.add(node)
    db.commit()
    db.refresh(node)
    return node


def get_speaker_node_by_id(db: Session, node_id: int) -> Optional[SpeakerNode]:
    node = db.query(SpeakerNode).filter(SpeakerNode.id == node_id).first()
    if node:
        refresh_node_online_statuses(db, [node])
    return node


HEARTBEAT_TIMEOUT_SECONDS = 15


def refresh_node_online_statuses(db: Session, nodes: List[SpeakerNode]) -> List[SpeakerNode]:
    """
    Dynamically computes and updates the online/offline status of speaker nodes
    based on the freshness of their last heartbeat timestamp.
    If last_heartbeat is within 15 seconds: ONLINE.
    Otherwise: OFFLINE.
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    changed = False
    for node in nodes:
        last_hb = node.last_heartbeat
        is_fresh = (
            last_hb is not None
            and (now - last_hb).total_seconds() <= HEARTBEAT_TIMEOUT_SECONDS
        )
        expected_status = "ONLINE" if is_fresh else "OFFLINE"
        if node.status != expected_status:
            node.status = expected_status
            changed = True
    if changed:
        try:
            db.commit()
        except Exception:
            db.rollback()
    return nodes


def get_speaker_node_by_mac(db: Session, mac_address: str) -> Optional[SpeakerNode]:
    clean_mac = mac_address.strip()
    return db.query(SpeakerNode).filter(SpeakerNode.mac_address.ilike(clean_mac)).first()


def get_all_speaker_nodes(
    db: Session,
    department_id: Optional[int] = None,
    zone: Optional[str] = None,
    status: Optional[str] = None,
) -> List[SpeakerNode]:
    # Ensure canonical 2-node inventory exists
    sync_canonical_speaker_nodes(db)

    query = db.query(SpeakerNode).filter(SpeakerNode.is_active == True)
    if department_id:
        query = query.filter(SpeakerNode.department_id == department_id)
    if zone and zone != "College-Wide":
        query = query.filter(SpeakerNode.zone == zone)

    nodes = query.order_by(SpeakerNode.id.asc()).all()
    nodes = refresh_node_online_statuses(db, nodes)

    if status:
        nodes = [n for n in nodes if n.status == status]
    return nodes


def update_speaker_node(db: Session, node: SpeakerNode, update_data: SpeakerNodeUpdate) -> SpeakerNode:
    data = update_data.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(node, key, value)
    db.commit()
    db.refresh(node)
    return node


def update_speaker_node_heartbeat(db: Session, heartbeat: SpeakerNodeHeartbeat) -> SpeakerNode:
    node = get_speaker_node_by_mac(db, heartbeat.mac_address)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    incoming_status = (heartbeat.status or "ONLINE").upper()

    if not node:
        node = SpeakerNode(
            name=f"Node {heartbeat.mac_address[-5:]}",
            mac_address=heartbeat.mac_address,
            ip_address=heartbeat.ip_address,
            zone="College-Wide",
            status=incoming_status,
            last_heartbeat=now if incoming_status == "ONLINE" else None,
        )
        db.add(node)
    else:
        node.ip_address = heartbeat.ip_address or node.ip_address
        node.status = incoming_status
        if heartbeat.cpu_usage is not None:
            node.cpu_usage = heartbeat.cpu_usage
        if heartbeat.memory_usage is not None:
            node.memory_usage = heartbeat.memory_usage
        if heartbeat.disk_space is not None:
            node.disk_space = heartbeat.disk_space
        if incoming_status == "ONLINE":
            node.last_heartbeat = now
        else:
            node.last_heartbeat = None

    db.commit()
    db.refresh(node)
    return node


def get_speaker_queue(db: Session, status: Optional[str] = None) -> List[SpeakerQueue]:
    query = db.query(SpeakerQueue)
    if status:
        query = query.filter(SpeakerQueue.status == status)
    return query.order_by(SpeakerQueue.queue_position.asc()).all()


def add_to_speaker_queue(
    db: Session,
    announcement_id: int,
    scheduled_time: Optional[datetime] = None,
    speaker_node_id: Optional[int] = None,
    status: Optional[str] = None,
    duration_seconds: Optional[int] = 0,
) -> SpeakerQueue:
    existing = db.query(SpeakerQueue).filter(SpeakerQueue.announcement_id == announcement_id).first()
    if existing:
        return existing

    max_pos = db.query(SpeakerQueue).count()
    active_playing = db.query(SpeakerQueue).filter(SpeakerQueue.status == "Playing").first()

    if status:
        item_status = status
    elif active_playing is None:
        item_status = "Playing"
    elif max_pos == 1:
        item_status = "Next in Queue"
    else:
        item_status = "Queued"

    queue_item = SpeakerQueue(
        announcement_id=announcement_id,
        speaker_node_id=speaker_node_id,
        queue_position=max_pos + 1,
        status=item_status,
        scheduled_time=scheduled_time or datetime.utcnow(),
        played_at=datetime.utcnow() if item_status == "Playing" else None,
        duration_seconds=duration_seconds or 0,
    )
    db.add(queue_item)
    db.commit()
    db.refresh(queue_item)
    return queue_item


def update_queue_item_status(
    db: Session,
    queue_id: int,
    status: str,
    failure_reason: Optional[str] = None,
) -> Optional[SpeakerQueue]:
    item = db.query(SpeakerQueue).filter(SpeakerQueue.id == queue_id).first()
    if not item:
        # Fallback 1: match by announcement_id
        item = db.query(SpeakerQueue).filter(SpeakerQueue.announcement_id == queue_id).first()
    if not item:
        # Fallback 2: if announcement exists with this ID, create the queue item dynamically
        from app.models.announcement import Announcement
        ann = db.query(Announcement).filter(Announcement.id == queue_id).first()
        if ann:
            max_pos = db.query(SpeakerQueue).count()
            words = len(((ann.title or "") + " " + (ann.description or "")).split())
            dur_secs = max(10, int(words / 2.5))
            item = SpeakerQueue(
                announcement_id=ann.id,
                queue_position=max_pos + 1,
                status=status,
                scheduled_time=datetime.utcnow(),
                played_at=datetime.utcnow() if status == "Playing" else None,
                duration_seconds=dur_secs,
            )
            db.add(item)
            db.commit()
            db.refresh(item)
            return item

    if item:
        item.status = status
        if status == "Playing":
            item.played_at = datetime.utcnow()
        if failure_reason:
            item.failure_reason = failure_reason
            item.error_count += 1
        db.commit()
        db.refresh(item)
    return item


def reorder_speaker_queue(db: Session, ordered_ids: List[int]) -> List[SpeakerQueue]:
    """
    Updates the queue_position of speaker queue items according to the provided ordered ID list.
    """
    items = []
    for pos, q_id in enumerate(ordered_ids, start=1):
        item = db.query(SpeakerQueue).filter(SpeakerQueue.id == q_id).first()
        if item:
            item.queue_position = pos
            items.append(item)
    db.commit()
    for item in items:
        db.refresh(item)
    return items


def delete_speaker_node(db: Session, node_id: int) -> bool:
    node = get_speaker_node_by_id(db, node_id)
    if not node:
        return False
    db.delete(node)
    db.commit()
    return True


def delete_speaker_queue_item(db: Session, queue_id: int) -> bool:
    item = db.query(SpeakerQueue).filter(SpeakerQueue.id == queue_id).first()
    if not item:
        return False
    db.delete(item)
    db.commit()
    return True


def clear_speaker_queue(db: Session, status: Optional[str] = None) -> int:
    query = db.query(SpeakerQueue)
    if status:
        query = query.filter(SpeakerQueue.status == status)
    deleted_count = query.delete(synchronize_session=False)
    db.commit()
    return deleted_count


def sync_canonical_speaker_nodes(db: Session) -> List[SpeakerNode]:
    """
    Enforces that canonical speaker nodes exist in EchoSphere:
    1. Wokwi ESP32 Speaker Node (MAC: 24:0A:C4:00:01:10)
    2. Hardware Speaker Client (MAC: D4:F3:2D:22:2A:CB)
    3. Hardware Speaker Client 2 (MAC: D4:F3:2D:22:2A:CC)
    Prunes stale, inactive test nodes to maintain a clean inventory.
    """
    canonical_specs = [
        {
            "name": "Wokwi ESP32 Speaker Node",
            "mac_address": "24:0A:C4:00:01:10",
            "ip_address": "10.0.1.15",
            "zone": "Block A - CSE Quad",
            "volume": 90,
            "disk_space": 72.5,
        },
        {
            "name": "Hardware Speaker Client",
            "mac_address": "D4:F3:2D:22:2A:CB",
            "ip_address": "127.0.0.1",
            "zone": "Auditorium / Campus",
            "volume": 85,
            "disk_space": 65.0,
        },
        {
            "name": "Hardware Speaker Client 2",
            "mac_address": "D4:F3:2D:22:2A:CC",
            "ip_address": "127.0.0.1",
            "zone": "Block B - AI Lab",
            "volume": 85,
            "disk_space": 65.0,
        },
    ]

    canonical_macs = [s["mac_address"].upper() for s in canonical_specs]

    # Prune any old non-canonical nodes that have never sent a heartbeat or are inactive
    all_nodes = db.query(SpeakerNode).all()
    for n in all_nodes:
        if str(n.mac_address).upper() not in canonical_macs and n.last_heartbeat is None:
            db.delete(n)
    db.commit()

    # Ensure all canonical nodes exist
    for spec in canonical_specs:
        existing = db.query(SpeakerNode).filter(SpeakerNode.mac_address.ilike(spec["mac_address"])).first()
        if not existing:
            new_node = SpeakerNode(
                name=spec["name"],
                mac_address=spec["mac_address"],
                ip_address=spec["ip_address"],
                zone=spec["zone"],
                volume=spec["volume"],
                status="OFFLINE",
                cpu_usage=0.0,
                memory_usage=0.0,
                disk_space=spec["disk_space"],
                last_heartbeat=None,
                is_active=True,
            )
            db.add(new_node)
        else:
            if existing.name != spec["name"]:
                setattr(existing, "name", spec["name"])
            if existing.zone != spec["zone"]:
                setattr(existing, "zone", spec["zone"])
    db.commit()

    nodes = db.query(SpeakerNode).order_by(SpeakerNode.id.asc()).all()
    return refresh_node_online_statuses(db, nodes)


def seed_default_speaker_nodes_if_empty(db: Session):
    sync_canonical_speaker_nodes(db)


