const cityStateData = {
    'Mumbai': 'Maharashtra', 'Delhi': 'Delhi', 'Bangalore': 'Karnataka',
    'Bengaluru': 'Karnataka', 'Hyderabad': 'Telangana', 'Ahmedabad': 'Gujarat',
    'Chennai': 'Tamil Nadu', 'Kolkata': 'West Bengal', 'Pune': 'Maharashtra',
    'Jaipur': 'Rajasthan', 'Surat': 'Gujarat', 'Lucknow': 'Uttar Pradesh',
    'Kanpur': 'Uttar Pradesh', 'Nagpur': 'Maharashtra', 'Indore': 'Madhya Pradesh',
    'Thane': 'Maharashtra', 'Bhopal': 'Madhya Pradesh', 'Visakhapatnam': 'Andhra Pradesh',
    'Pimpri-Chinchwad': 'Maharashtra', 'Patna': 'Bihar', 'Vadodara': 'Gujarat',
    'Ghaziabad': 'Uttar Pradesh', 'Ludhiana': 'Punjab', 'Agra': 'Uttar Pradesh',
    'Nashik': 'Maharashtra', 'Faridabad': 'Haryana', 'Meerut': 'Uttar Pradesh',
    'Rajkot': 'Gujarat', 'Kalyan-Dombivali': 'Maharashtra', 'Vasai-Virar': 'Maharashtra',
    'Varanasi': 'Uttar Pradesh', 'Srinagar': 'Jammu and Kashmir', 'Aurangabad': 'Maharashtra',
    'Dhanbad': 'Jharkhand', 'Amritsar': 'Punjab', 'Navi Mumbai': 'Maharashtra',
    'Allahabad': 'Uttar Pradesh', 'Prayagraj': 'Uttar Pradesh', 'Ranchi': 'Jharkhand',
    'Howrah': 'West Bengal', 'Coimbatore': 'Tamil Nadu', 'Jabalpur': 'Madhya Pradesh',
    'Gwalior': 'Madhya Pradesh', 'Vijayawada': 'Andhra Pradesh', 'Jodhpur': 'Rajasthan',
    'Madurai': 'Tamil Nadu', 'Raipur': 'Chhattisgarh', 'Kota': 'Rajasthan',
    'Chandigarh': 'Chandigarh', 'Guwahati': 'Assam', 'Solapur': 'Maharashtra',
    'Hubli-Dharwad': 'Karnataka', 'Mysore': 'Karnataka', 'Mysuru': 'Karnataka',
    'Tiruchirappalli': 'Tamil Nadu', 'Bareilly': 'Uttar Pradesh', 'Aligarh': 'Uttar Pradesh',
    'Tiruppur': 'Tamil Nadu', 'Moradabad': 'Uttar Pradesh', 'Jalandhar': 'Punjab',
    'Bhubaneswar': 'Odisha', 'Salem': 'Tamil Nadu', 'Warangal': 'Telangana',
    'Guntur': 'Andhra Pradesh', 'Bhiwandi': 'Maharashtra', 'Saharanpur': 'Uttar Pradesh',
    'Gorakhpur': 'Uttar Pradesh', 'Bikaner': 'Rajasthan', 'Amravati': 'Maharashtra',
    'Noida': 'Uttar Pradesh', 'Jamshedpur': 'Jharkhand', 'Bhilai': 'Chhattisgarh',
    'Cuttack': 'Odisha', 'Firozabad': 'Uttar Pradesh', 'Kochi': 'Kerala',
    'Nellore': 'Andhra Pradesh', 'Bhavnagar': 'Gujarat', 'Dehradun': 'Uttarakhand',
    'Durgapur': 'West Bengal', 'Asansol': 'West Bengal', 'Rourkela': 'Odisha',
    'Nanded': 'Maharashtra', 'Kolhapur': 'Maharashtra', 'Ajmer': 'Rajasthan',
    'Akola': 'Maharashtra', 'Gulbarga': 'Karnataka', 'Jamnagar': 'Gujarat',
    'Ujjain': 'Madhya Pradesh', 'Loni': 'Uttar Pradesh', 'Siliguri': 'West Bengal',
    'Jhansi': 'Uttar Pradesh', 'Ulhasnagar': 'Maharashtra', 'Jammu': 'Jammu and Kashmir',
    'Sangli-Miraj & Kupwad': 'Maharashtra', 'Mangalore': 'Karnataka', 'Erode': 'Tamil Nadu',
    'Belgaum': 'Karnataka', 'Ambattur': 'Tamil Nadu', 'Tirunelveli': 'Tamil Nadu',
    'Malegaon': 'Maharashtra', 'Gaya': 'Bihar', 'Jalgaon': 'Maharashtra',
    'Udaipur': 'Rajasthan', 'Maheshtala': 'West Bengal', 'Thiruvananthapuram': 'Kerala'
};

const cityList  = document.getElementById('cityList');
const cityInput = document.getElementById('cityInput');
const stateInput = document.getElementById('stateInput');

Object.keys(cityStateData).sort().forEach(city => {
    const option = document.createElement('option');
    option.value = city;
    cityList.appendChild(option);
});

function autoFillState(cityVal, stateField) {
    const city = cityVal.trim();
    if (cityStateData[city]) {
        stateField.value = cityStateData[city];
    } else {
        const key = Object.keys(cityStateData).find(k => k.toLowerCase() === city.toLowerCase());
        stateField.value = key ? cityStateData[key] : '';
    }
}

cityInput.addEventListener('input', function () {
    autoFillState(this.value, stateInput);
});

cityInput.addEventListener('change', function () {
    autoFillState(this.value, stateInput);
});

const dobDisplay = document.getElementById('dobDisplay');
const dobHidden  = document.getElementById('dobHidden');
const dobError   = document.getElementById('dobError');
const customerForm = document.getElementById('customerForm');

dobDisplay.addEventListener('input', function (e) {
    let v = e.target.value.replace(/\D/g, '');
    if (v.length >= 2) v = v.slice(0, 2) + '/' + v.slice(2);
    if (v.length >= 5) v = v.slice(0, 5) + '/' + v.slice(5, 9);
    e.target.value = v;
    dobError.style.display = 'none';
    dobDisplay.style.borderColor = '';
});

dobDisplay.addEventListener('blur', validateAndConvertDate);

function validateAndConvertDate() {
    const parts = dobDisplay.value.split('/');
    if (parts.length === 3) {
        const day = parseInt(parts[0], 10);
        const month = parseInt(parts[1], 10);
        const year = parseInt(parts[2], 10);
        if (day >= 1 && day <= 31 && month >= 1 && month <= 12 && year >= 1900 && year <= 2100) {
            const iso = `${year}-${String(month).padStart(2,'0')}-${String(day).padStart(2,'0')}`;
            const d = new Date(iso);
            if (d.getFullYear() === year && d.getMonth() + 1 === month && d.getDate() === day) {
                const today = new Date();
                let age = today.getFullYear() - d.getFullYear();
                if (today.getMonth() < d.getMonth() || (today.getMonth() === d.getMonth() && today.getDate() < d.getDate())) age--;
                if (age >= 18) {
                    dobHidden.value = iso;
                    dobError.style.display = 'none';
                    dobDisplay.style.borderColor = '';
                    return true;
                }
            }
        }
    }
    dobHidden.value = '';
    return false;
}

const nomineeYes = document.getElementById('nomineeYes');
const nomineeNo  = document.getElementById('nomineeNo');
const nomineesSection = document.getElementById('nomineesSection');
const nomineeFormsContainer = document.getElementById('nomineeFormsContainer');
const nomineeCountBtns = document.querySelectorAll('.nominee-count-btn');

nomineeYes.addEventListener('change', function () {
    if (this.checked) { nomineesSection.style.display = 'block'; generateNomineeForms(1); }
});
nomineeNo.addEventListener('change', function () {
    if (this.checked) { nomineesSection.style.display = 'none'; nomineeFormsContainer.innerHTML = ''; }
});

nomineeCountBtns.forEach(btn => {
    btn.addEventListener('click', function () {
        nomineeCountBtns.forEach(b => b.classList.remove('active'));
        this.classList.add('active');
        generateNomineeForms(parseInt(this.dataset.count));
    });
});

function generateNomineeForms(count) {
    nomineeFormsContainer.innerHTML = '';
    for (let i = 1; i <= count; i++) nomineeFormsContainer.appendChild(createNomineeForm(i));
}

function createNomineeForm(index) {
    const card = document.createElement('div');
    card.className = 'nominee-card';
    card.innerHTML = `
        <div class="nominee-card-header">
            <h3 class="nominee-card-title">Nominee ${index}</h3>
        </div>
        <div class="form-row">
            <div class="form-group">
                <label>Nominee Name <span class="required">*</span></label>
                <input type="text" name="nominee_name_${index}" class="form-control" placeholder="Enter nominee name" required>
            </div>
            <div class="form-group">
                <label>Relation <span class="required">*</span></label>
                <select name="nominee_relation_${index}" class="form-control" required>
                    <option value="">Select Relation</option>
                    <option value="Father">Father</option>
                    <option value="Mother">Mother</option>
                    <option value="Spouse">Spouse</option>
                    <option value="Son">Son</option>
                    <option value="Daughter">Daughter</option>
                    <option value="Brother">Brother</option>
                    <option value="Sister">Sister</option>
                    <option value="Other">Other</option>
                </select>
            </div>
        </div>
        <div class="form-row">
            <div class="form-group">
                <label>Phone Number</label>
                <input type="text" name="nominee_phone_${index}" class="form-control" placeholder="10 digit phone number" maxlength="10">
            </div>
            <div class="form-group">
                <label>Email</label>
                <input type="email" name="nominee_email_${index}" class="form-control" placeholder="nominee@email.com">
            </div>
        </div>
        <div class="form-row">
            <div class="form-group">
                <label>Aadhaar Number <span class="required">*</span></label>
                <input type="text" name="nominee_aadhaar_${index}" class="form-control" placeholder="12 digit Aadhaar number" maxlength="12" required>
            </div>
            <div class="form-group">
                <label>Flat/House No</label>
                <input type="text" name="nominee_flat_${index}" class="form-control" placeholder="Enter flat/house number">
            </div>
        </div>
        <div class="form-row">
            <div class="form-group">
                <label>City</label>
                <input type="text" name="nominee_city_${index}" class="form-control nominee-city" placeholder="Select or type city" list="cityList" autocomplete="off">
            </div>
            <div class="form-group">
                <label>State</label>
                <input type="text" name="nominee_state_${index}" class="form-control nominee-state" placeholder="State (auto-filled)" readonly>
            </div>
        </div>
        <div class="form-row">
            <div class="form-group">
                <label>Pin Code</label>
                <input type="text" name="nominee_pincode_${index}" class="form-control" placeholder="6 digit pin code" maxlength="6">
            </div>
        </div>`;

    setTimeout(() => {
        const cf = card.querySelector('.nominee-city');
        const sf = card.querySelector('.nominee-state');
        cf.addEventListener('input', function () { autoFillState(this.value, sf); });
cf.addEventListener('change', function () { autoFillState(this.value, sf); });
    }, 100);

    return card;
}

customerForm.addEventListener('submit', function (e) {
    const valid = validateAndConvertDate();
    if (!valid || !dobHidden.value) {
        e.preventDefault();
        dobError.style.display = 'block';
        dobDisplay.style.borderColor = 'var(--danger)';
        dobDisplay.focus();
        dobDisplay.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
});