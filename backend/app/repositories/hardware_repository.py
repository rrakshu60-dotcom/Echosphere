from datetime import datetime
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
        last_heartbeat=datetime.utcnow(),
    )
    db.add(node)
    db.commit()
    db.refresh(node)
    return node


def get_speaker_node_by_id(db: Session, node_id: int) -> Optional[SpeakerNode]:
    return db.query(SpeakerNode).filter(SpeakerNode.id == node_id).first()


def get_speaker_node_by_mac(db: Session, mac_address: str) -> Optional[SpeakerNode]:
    return db.query(SpeakerNode).filter(SpeakerNode.mac_address == mac_address).first()


def get_all_speaker_nodes(
    db: Session,
    department_id: Optional[int] = None,
    zone: Optional[str] = None,
    status: Optional[str] = None,
) -> List[SpeakerNode]:
    query = db.query(SpeakerNode).filter(SpeakerNode.is_active == True)
    if department_id:
        query = query.filter(SpeakerNode.department_id == department_id)
    if zone and zone != "College-Wide":
        query = query.filter(SpeakerNode.zone == zone)
    if status:
        query = query.filter(SpeakerNode.status == status)
    return query.order_by(SpeakerNode.name).all()


def update_speaker_node(db: Session, node: SpeakerNode, update_data: SpeakerNodeUpdate) -> SpeakerNode:
    data = update_data.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(node, key, value)
    db.commit()
    db.refresh(node)
    return node


def update_speaker_node_heartbeat(db: Session, heartbeat: SpeakerNodeHeartbeat) -> SpeakerNode:
    node = get_speaker_node_by_mac(db, heartbeat.mac_address)
    if not node:
        # Auto-register node if unknown MAC
        node = SpeakerNode(
            name=f"Node {heartbeat.mac_address[-5:]}",
            mac_address=heartbeat.mac_address,
            ip_address=heartbeat.ip_address,
            zone="College-Wide",
            status=heartbeat.status or "ONLINE",
            last_heartbeat=datetime.utcnow(),
        )
        db.add(node)
    else:
        node.ip_address = heartbeat.ip_address or node.ip_address
        node.status = heartbeat.status or "ONLINE"
        node.cpu_usage = heartbeat.cpu_usage
        node.memory_usage = heartbeat.memory_usage
        node.disk_space = heartbeat.disk_space
        node.last_heartbeat = datetime.utcnow()

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
) -> SpeakerQueue:
    existing = db.query(SpeakerQueue).filter(SpeakerQueue.announcement_id == announcement_id).first()
    if existing:
        return existing

    max_pos = db.query(SpeakerQueue).count()
    queue_item = SpeakerQueue(
        announcement_id=announcement_id,
        speaker_node_id=speaker_node_id,
        queue_position=max_pos + 1,
        status="Queued",
        scheduled_time=scheduled_time or datetime.utcnow(),
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
    if item:
        item.status = status
        if status == "Playing":
            item.played_at = datetime.utcnow()
        if failure_reason:
            item.failure_reason = failure_reason
            item.error_count += 1
        db.commit()
        db.refresh(item)
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

