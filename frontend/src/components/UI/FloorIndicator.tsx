import { useDraftStore } from '../../store/draftStore';
export function FloorIndicator() {
 const {draft,selectFloor}=useDraftStore();
 return <label className="level-control"><span>Level</span><select aria-label="Visible level" value={draft.selectedFloor===null?'exterior':draft.selectedFloor} onChange={e=>selectFloor(e.target.value==='exterior'?null:Number(e.target.value))}><option value="exterior">All office</option>{Array.from({length:draft.floors},(_,i)=><option key={i} value={i}>{i+1} / {draft.floors}</option>)}</select></label>;
}
export default FloorIndicator;
