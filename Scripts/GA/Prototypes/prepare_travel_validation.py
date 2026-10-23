"""Release read-only inspection locals before seamless travel garbage collection."""
for _qa_name in ('pcs','p','row','asc','hit','result','pc','menu','controller','trees','tree','entries','index','cls'):
    globals().pop(_qa_name,None)
