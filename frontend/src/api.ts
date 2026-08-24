export type Mode = 'single_html' | 'multi_page' | 'react'
export type Project = {id:string;name:string;prompt:string;mode:Mode;active_version:number|null;created_at:string;updated_at:string}
export type Job = {id:string;project_id:string;kind:string;status:string;error:string|null}
export type SiteFile = {path:string;content:string;bytes:number;sha256:string}

async function request<T>(path:string, init?:RequestInit):Promise<T> {
  const response = await fetch(path, {headers:{'Content-Type':'application/json',...(init?.headers||{})},...init})
  if (!response.ok) throw new Error((await response.json().catch(()=>null))?.detail || `Request failed: ${response.status}`)
  return response.json()
}
export const api = {
  projects:()=>request<Project[]>('/api/projects'),
  project:(id:string)=>request<Project>(`/api/projects/${id}`),
  create:(body:{name:string;prompt:string;mode:Mode})=>request<Project>('/api/projects',{method:'POST',body:JSON.stringify(body)}),
  generate:(id:string)=>request<Job>(`/api/projects/${id}/generate`,{method:'POST'}),
  revise:(id:string, instruction:string, selected:unknown)=>request<Job>(`/api/projects/${id}/revisions`,{method:'POST',body:JSON.stringify({instruction,selected_element:selected})}),
  files:(id:string)=>request<{version:number|null;files:SiteFile[]}>(`/api/projects/${id}/files`),
  deploy:(id:string)=>request<{url:string;slug:string;version:number}>(`/api/projects/${id}/deploy`,{method:'POST'}),
}

