import os
from datetime import date, datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, DateTime, ForeignKey, func
from sqlalchemy.orm import declarative_base, sessionmaker
import secrets

url=os.getenv("DATABASE_URL","sqlite:///./lanchebar.db").replace("postgresql://","postgresql+psycopg://",1).replace("postgres://","postgresql+psycopg://",1)
engine=create_engine(url,connect_args={"check_same_thread":False} if url.startswith("sqlite") else {},pool_pre_ping=True)
Session=sessionmaker(bind=engine)
Base=declarative_base()
class Product(Base):
 __tablename__="products"
 id=Column(Integer,primary_key=True)
 name=Column(String(140),nullable=False)
 category=Column(String(80),default="Geral")
 barcode=Column(String(80))
 price=Column(Float,default=0)
 minimum=Column(Float,default=0)
class Lot(Base):
 __tablename__="lots"
 id=Column(Integer,primary_key=True)
 product_id=Column(Integer,ForeignKey("products.id"))
 quantity=Column(Float,default=0)
 expiry=Column(Date)
 batch=Column(String(80))
class Movement(Base):
 __tablename__="movements"
 id=Column(Integer,primary_key=True)
 product_id=Column(Integer,ForeignKey("products.id"))
 quantity=Column(Float)
 kind=Column(String(20))
 created=Column(DateTime,default=datetime.utcnow)
class DiningTable(Base):
 __tablename__="tables"
 id=Column(Integer,primary_key=True)
 label=Column(String(30))
class Order(Base):
 __tablename__="orders"
 id=Column(Integer,primary_key=True)
 table_id=Column(Integer,ForeignKey("tables.id"))
 status=Column(String(20),default="aberto")
 total=Column(Float,default=0)
class Item(Base):
 __tablename__="items"
 id=Column(Integer,primary_key=True)
 order_id=Column(Integer,ForeignKey("orders.id"))
 product_id=Column(Integer,ForeignKey("products.id"))
 quantity=Column(Float)
 price=Column(Float)
class Payment(Base):
 __tablename__="payments"
 id=Column(Integer,primary_key=True)
 order_id=Column(Integer,ForeignKey("orders.id"))
 method=Column(String(30))
 amount=Column(Float)
 created=Column(DateTime,default=datetime.utcnow)
Base.metadata.create_all(engine)
app=FastAPI(title="LancheBar Cloud — demonstração acadêmica")
auth=HTTPBasic()
def db():
 s=Session()
 try: yield s
 finally: s.close()
def user(c:HTTPBasicCredentials=Depends(auth)):
 u=os.getenv("ADMIN_USER","admin"); p=os.getenv("ADMIN_PASSWORD")
 if not p or not(secrets.compare_digest(c.username,u) and secrets.compare_digest(c.password,p)):
  raise HTTPException(401,"Credenciais inválidas ou ADMIN_PASSWORD não configurada",headers={"WWW-Authenticate":"Basic"})
 return c.username
@app.on_event("startup")
def seed():
 s=Session()
 if not s.query(DiningTable).first():
  s.add_all([DiningTable(label=f"Mesa {n}") for n in range(1,13)]);s.commit()
 s.close()
@app.get("/",response_class=HTMLResponse)
def home():
 from pathlib import Path
 return Path("app/static/index.html").read_text(encoding="utf-8")
@app.get("/api/health")
def health():return {"status":"ok"}
@app.get("/api/products")
def products(s=Depends(db),u=Depends(user)):
 return [{"id":p.id,"name":p.name,"category":p.category,"price":p.price,"minimum":p.minimum,"stock":sum(x.quantity for x in s.query(Lot).filter_by(product_id=p.id))} for p in s.query(Product).order_by(Product.name)]
@app.post("/api/products")
def product_add(d:dict,s=Depends(db),u=Depends(user)):
 if not str(d.get("name","")).strip():raise HTTPException(400,"Nome obrigatório")
 p=Product(name=d["name"],category=d.get("category","Geral"),barcode=d.get("barcode"),price=float(d.get("price",0)),minimum=float(d.get("minimum",0)))
 s.add(p);s.commit();return {"id":p.id}
@app.post("/api/stock/in")
def stock_in(d:dict,s=Depends(db),u=Depends(user)):
 p=s.get(Product,int(d["product_id"]));q=float(d["quantity"])
 if not p or q<=0:raise HTTPException(400,"Produto ou quantidade inválida")
 expiry=date.fromisoformat(d["expiry"]) if d.get("expiry") else None
 s.add(Lot(product_id=p.id,quantity=q,expiry=expiry,batch=d.get("batch")))
 s.add(Movement(product_id=p.id,quantity=q,kind="entrada"));s.commit();return {"ok":True}
def deduct(s,pid,q):
 lots=s.query(Lot).filter(Lot.product_id==pid,Lot.quantity>0).order_by(Lot.expiry.is_(None),Lot.expiry,Lot.id).all()
 if sum(x.quantity for x in lots)<q:raise HTTPException(400,"Estoque insuficiente")
 for lot in lots:
  n=min(q,lot.quantity);lot.quantity-=n;q-=n;s.add(Movement(product_id=pid,quantity=n,kind="saida"))
  if q<=0:break
@app.post("/api/stock/out")
def stock_out(d:dict,s=Depends(db),u=Depends(user)):
 q=float(d["quantity"])
 if q<=0:raise HTTPException(400,"Quantidade inválida")
 deduct(s,int(d["product_id"]),q);s.commit();return {"ok":True}
@app.get("/api/expiry")
def expiry(days:int=30,s=Depends(db),u=Depends(user)):
 today=date.today();end=today+timedelta(days=max(0,min(days,365)))
 return [{"product":s.get(Product,x.product_id).name,"quantity":x.quantity,"expiry":x.expiry.isoformat(),"expired":x.expiry<today} for x in s.query(Lot).filter(Lot.quantity>0,Lot.expiry!=None,Lot.expiry<=end).order_by(Lot.expiry)]
@app.get("/api/movements")
def movements(s=Depends(db),u=Depends(user)):
 return [{"product":s.get(Product,m.product_id).name,"kind":m.kind,"quantity":m.quantity,"date":m.created.isoformat()} for m in s.query(Movement).order_by(Movement.id.desc()).limit(100)]
@app.get("/api/tables")
def tables(s=Depends(db),u=Depends(user)):
 return [{"id":t.id,"label":t.label,"order_id":o.id if o else None,"total":o.total if o else 0} for t in s.query(DiningTable) for o in [s.query(Order).filter(Order.table_id==t.id,Order.status!="fechado").first()]]
@app.post("/api/orders")
def add_order(d:dict,s=Depends(db),u=Depends(user)):
 tid=int(d["table_id"]);t=s.get(DiningTable,tid)
 if not t:raise HTTPException(404,"Mesa inexistente")
 o=s.query(Order).filter(Order.table_id==tid,Order.status!="fechado").first()
 if not o:o=Order(table_id=tid);s.add(o);s.flush()
 for x in d.get("items",[]):
  p=s.get(Product,int(x["product_id"]));q=float(x["quantity"])
  if not p or q<=0:raise HTTPException(400,"Item inválido")
  s.add(Item(order_id=o.id,product_id=p.id,quantity=q,price=p.price));o.total+=q*p.price
 s.commit();return {"order_id":o.id,"total":o.total}
@app.get("/api/orders")
def orders(s=Depends(db),u=Depends(user)):
 return [{"id":o.id,"table":s.get(DiningTable,o.table_id).label,"total":o.total,"status":o.status,"items":[{"name":s.get(Product,i.product_id).name,"quantity":i.quantity} for i in s.query(Item).filter_by(order_id=o.id)]} for o in s.query(Order).filter(Order.status!="fechado")]
@app.post("/api/orders/{oid}/close")
def close(oid:int,d:dict,s=Depends(db),u=Depends(user)):
 o=s.get(Order,oid)
 if not o or o.status=="fechado":raise HTTPException(404,"Comanda inexistente")
 amount=float(d.get("amount",0))
 if amount<o.total:raise HTTPException(400,"Pagamento insuficiente")
 for i in s.query(Item).filter_by(order_id=o.id):
  if s.query(Lot).filter(Lot.product_id==i.product_id,Lot.quantity>0).first():deduct(s,i.product_id,i.quantity)
 s.add(Payment(order_id=o.id,method=d.get("method","dinheiro"),amount=o.total))
 o.status="fechado";s.commit();return {"ok":True,"change":round(amount-o.total,2)}
@app.get("/api/dashboard")
def dashboard(s=Depends(db),u=Depends(user)):
 return {"products":s.query(Product).count(),"orders_open":s.query(Order).filter(Order.status!="fechado").count(),"expiring":len(expiry(30,s,u)),"revenue":float(s.query(func.coalesce(func.sum(Payment.amount),0)).scalar())}
