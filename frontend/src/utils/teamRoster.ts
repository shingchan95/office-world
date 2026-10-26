export interface TeamAvatar { id:string; name:string; teams:string[]; color:string }
const COLORS=['#68bba9','#e4a076','#8e9ed3','#d08bb0','#d4b45f','#7eafcc'];
export function teamRoster(value: unknown): TeamAvatar[] {
 if (!Array.isArray(value)) throw new Error('Invalid teams response');
 const agents=new Map<string,TeamAvatar>();
 for (const [index,team] of value.entries()) {
  if (!team || typeof team!=='object') continue;
  if (!['planned','active'].includes(team.status)) continue;
  if (!Array.isArray(team.members)) continue;
  const teamName=typeof team.name==='string'?team.name:typeof team.slug==='string'?team.slug:'Office team';
  for (const name of team.members) {
   if(typeof name!=='string'||!name.trim())continue;
   let avatar=agents.get(name);
   if(!avatar){avatar={id:name,name,teams:[],color:COLORS[index%COLORS.length]};agents.set(name,avatar);}
   if(!avatar.teams.includes(teamName))avatar.teams.push(teamName);
  }
 }
 return [...agents.values()].sort((a,b)=>a.id.localeCompare(b.id));
}
