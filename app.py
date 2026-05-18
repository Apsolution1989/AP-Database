import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# นำเข้าไลบรารีสำหรับอัปโหลดไฟล์เข้า Google Drive
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

# ตั้งค่าหน้าจอ
st.set_page_config(page_title="Material Cost Tracker", layout="centered")
st.title("AP Solution(1989) Co.,Ltd.")
st.subheader("ระบบบริหารจัดการฐานข้อมูลวัสดุ (Auto-Upload to Cloud)")

# ดึงข้อมูลโฟลเดอร์เป้าหมายจาก Secrets
FOLDER_ID = st.secrets.get("FOLDER_ID", "")

# 💡 ฟังก์ชันภายในสำหรับการอัปโหลดไฟล์ขึ้น Google Drive โดยตรง
def upload_to_google_drive(uploaded_file):
    try:
        # ใช้ข้อมูลสิทธิ์จาก connections.gsheets ที่ตั้งค่าไว้แล้วมาล็อกอินเข้า Drive API
        creds_info = st.secrets["connections"]["gsheets"]
        creds = service_account.Credentials.from_service_account_info(creds_info)
        
        # สร้างตัวเชื่อมต่อกับ Google Drive API
        drive_service = build('drive', 'v3', credentials=creds)
        
        # ตั้งค่าคุณสมบัติไฟล์ (ชื่อไฟล์ และ โฟลเดอร์ปลายทาง)
        file_metadata = {
            'name': f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uploaded_file.name}",
            'parents': [FOLDER_ID] if FOLDER_ID else []
        }
        
        # เตรียมเนื้อหาไฟล์
        media = MediaIoBaseUpload(
            io.BytesIO(uploaded_file.read()), 
            mimetype=uploaded_file.type, 
            resumable=True
        )
        
        # สั่งอัปโหลดไฟล์
        file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()
        
        # สั่งเปิดสิทธิ์แชร์ให้ "ทุกคนที่มีลิงก์" สามารถกดดูรูปนี้ได้
        try:
            drive_service.permissions().create(
                fileId=file.get('id'),
                body={'type': 'anyone', 'role': 'reader'}
            ).execute()
        except:
            pass # ถ้าเปิดสิทธิ์ไม่ผ่านให้ข้ามไปก่อน
            
        return file.get('webViewLink') # ส่งลิงก์ไฟล์บนคลาวด์กลับไปบันทึกใน Sheet
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการอัปโหลดเข้า Google Drive: {e}")
        return None

# เชื่อมต่อ Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# เมนูระบบ
menu = ["Request (ขอวัสดุ)", "บันทึกข้อมูล (Supplier/ราคา)", "เรียกดูข้อมูลทั้งหมด"]
choice = st.sidebar.selectbox("เมนูระบบ", menu)

# ====================================================================
# เมนูที่ 1: Request (ขอวัสดุ)
# ====================================================================
if choice == "Request (ขอวัสดุ)":
    st.markdown("### 📝 สร้างรายการขอวัสดุใหม่ (Material Request)")
    with st.form(key="request_form"):
        type_val = st.selectbox("ประเภทวัสดุ", ["Piping", "Electrical", "Structural", "Other"])
        project_val = st.text_input("ชื่อโครงการ (Project Name)")
        request_val = st.text_area("รายการวัสดุที่ต้องการ (Material Request)")
        submit_req = st.form_submit_button(label="บันทึกใบขอวัสดุ")

    if submit_req:
        if not project_val or not request_val:
            st.error("❌ กรุณากรอกชื่อ Project และรายละเอียดให้ครบถ้วน")
        else:
            new_req = pd.DataFrame([{
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Type": type_val,
                "Project": project_val,
                "Material Request": request_val,
                "Supplier Detail": "-",
                "Price": 0.0,
                "Attachment Link": "-"
            }])
            existing_data = conn.read(worksheet="Sheet1", ttl=0)
            updated_df = pd.concat([existing_data, new_req], ignore_index=True)
            conn.update(worksheet="Sheet1", data=updated_df)
            st.success("🎉 บันทึกรายการเรียบร้อยแล้ว!")
            st.rerun()

# ====================================================================
# เมนูที่ 2: บันทึกข้อมูล (Supplier/ราคา) -> อัปโหลดเข้าคลาวด์อัตโนมัติ
# ====================================================================
elif choice == "บันทึกข้อมูล (Supplier/ราคา)":
    st.markdown("### 🏷️ อัปเดตข้อมูลซัพพลายเออร์ ราคา และไฟล์หลักฐาน")
    data = conn.read(worksheet="Sheet1", ttl=0)
    
    if not data.empty and "Material Request" in data.columns:
        pending_data = data[(data["Supplier Detail"] == "-") | (data["Price"] == 0)]
        
        if pending_data.empty:
            st.info("✅ ไม่มีรายการค้างบันทึกราคาในระบบขณะนี้")
        else:
            pending_list = pending_data.apply(lambda r: f"[{r['Project']}] {r['Material Request'][:30]}...", axis=1).tolist()
            selected_option = st.selectbox("รายการที่ค้างดำเนินการ", pending_list)
            
            selected_index = pending_data.index[pending_list.index(selected_option)]
            row_info = data.loc[selected_index]
            
            st.info(f"📋 **รายละเอียดงาน:**\n* **โครงการ:** {row_info['Project']}\n* **วัสดุที่ขอ:** {row_info['Material Request']}")
            
            with st.form(key="supplier_form"):
                supplier_val = st.text_area("รายละเอียดผู้ขาย / สเปกเพิ่มเติม (Supplier Detail)")
                price_val = st.number_input("ยอดราคาสุทธิ (บาท)", min_value=0.0, format="%.2f")
                
                st.markdown("---")
                st.markdown("☁️ **อัปโหลดไฟล์เข้า Google Drive อัตโนมัติ**")
                uploaded_file = st.file_uploader("เลือกไฟล์รูปภาพหรือเอกสารอ้างอิง (PDF, PNG, JPG)", type=["pdf", "png", "jpg", "jpeg"])
                
                submit_supplier = st.form_submit_button(label="อัปเดตข้อมูลและส่งไฟล์เข้าคลาวด์")
            
            if submit_supplier:
                if not supplier_val or price_val <= 0:
                    st.error("❌ กรุณากรอกรายละเอียด Supplier และระบุราคาให้ถูกต้อง")
                else:
                    final_link = "-"
                    
                    # ถ้ามีการเลือกไฟล์เข้ามา ให้สลับไปเรียกฟังก์ชันอัปโหลดขึ้น Drive ทันที
                    if uploaded_file is not None:
                        with st.spinner("⏳ กำลังส่งไฟล์เข้าสู่โฟลเดอร์ Google Drive ของบริษัท..."):
                            cloud_url = upload_to_google_drive(uploaded_file)
                            if cloud_url:
                                final_link = cloud_url
                            else:
                                final_link = "เกิดข้อผิดพลาดในการอัปโหลด"
                    
                    # อัปเดตข้อมูลตาราง
                    data.at[selected_index, "Supplier Detail"] = supplier_val
                    data.at[selected_index, "Price"] = price_val
                    data.at[selected_index, "Attachment Link"] = final_link
                    data.at[selected_index, "Timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    conn.update(worksheet="Sheet1", data=data)
                    st.success("💾 ระบบทำการอัปโหลดไฟล์และอัปเดตฐานข้อมูลสำเร็จเรียบร้อยแล้ว!")
                    st.rerun()
    else:
        st.warning("⚠️ ไม่พบโครงสร้างตารางหลักในระบบ")

# ====================================================================
# เมนูที่ 3: เรียกดูข้อมูลทั้งหมด
# ====================================================================
elif choice == "เรียกดูข้อมูลทั้งหมด":
    st.markdown("### 📊 คลังฐานข้อมูลวัสดุทั้งหมด")
    data = conn.read(worksheet="Sheet1", ttl=0)
    
    if not data.empty and "Project" in data.columns:
        project_filter = st.multiselect("กรองดูเฉพาะโครงการที่ต้องการ", options=data["Project"].unique())
        if project_filter:
            data = data[data["Project"].isin(project_filter)]
        
        st.dataframe(data, use_container_width=True)
        
        st.markdown("---")
        st.markdown("🔗 **คลิกเปิดดูไฟล์แนบของรายการที่ต้องการ:**")
        valid_links = data[data["Attachment Link"].str.contains("http", na=False)]
        
        if not valid_links.empty:
            for idx, row in valid_links.iterrows():
                st.link_button(f"🔗 ดูหลักฐานของ [{row['Project']}] - {row['Material Request'][:20]}...", row["Attachment Link"])
        else:
            st.text("ไม่มีไฟล์แนบในระบบขณะนี้")
            
        if "Price" in data.columns:
            total_price = pd.to_numeric(data["Price"]).sum()
            st.metric("มูลค่าราคารวมในระบบขณะนี้", f"{total_price:,.2f} บาท")
