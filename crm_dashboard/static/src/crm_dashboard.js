/** @odoo-module **/

import { Component, useState, onMounted ,useRef,onWillStart} from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import { session } from "@web/session";
import { user } from "@web/core/user";
import { registry } from "@web/core/registry";
import { loadJS } from "@web/core/assets";
import { useService } from "@web/core/utils/hooks";
export class CrmDashboard extends Component {
    setup() {

       
        this.action = useService("action");
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        
        let currentMonth = String(new Date().getMonth() + 1).padStart(2, '0');

        
        this.Onclick_get_activity_view = this.Onclick_get_activity_view.bind(this);
        this.Onclick_get_probability_values = this.Onclick_get_probability_values.bind(this);
        this.onclick_employee_payment_collection = this.onclick_employee_payment_collection.bind(this);
        this.Onclick_new_get_employee_payment_totals = this.Onclick_new_get_employee_payment_totals.bind(this);
        this.Onclick_get_realization_summary=this.Onclick_get_realization_summary.bind(this);
        
        this.chartRefQuoteCompany = useRef("chartQuoteCompany");
        this.chartRefWonStage = useRef("chartWonStage");
        this.chartRefQuoteProduct = useRef("chartQuoteProduct");
        this.chartRefforecastCompany = useRef("chartforecastCompany");
        this.chartRefforecastProduct = useRef("chartforecastProduct");


        this.state=useState({
            currency_name: '',
            selected_company_id:0,
            selected_product_id:0,
            selected_job_id:0,
            selected_team_id:0,
            selected_employee_id:0,
            current_month:currentMonth,
            isFilterHidden: false,
            domain:[],
            filter_by:{
                b1:'year',
                b2:'year',
                b3:'year',
                b4:'year',
                b5:'year',
            },
            
            team_id:null,
            comp_id:null,
            user_id:null,
            isAdmin:null,
            userId:null,

            filterLists: [],
                
           month_list :[
                { id: "01", name: "January" },
                { id: "02", name: "February" },
                { id: "03", name: "March" },
                { id: "04", name: "April" },
                { id: "05", name: "May" },
                { id: "06", name: "June" },
                { id: "07", name: "July" },
                { id: "08", name: "August" },
                { id: "09", name: "September" },
                { id: "10", name: "October" },
                { id: "11", name: "November" },
                { id: "12", name: "December" },
            ],
            available_month:[],
            forecast_load:true,
            forecastmonth_list :[],
            
            select_month:currentMonth,
            new_select_month:currentMonth,
           
            
            select_month_revenue:null,

            select_month_forecast:null,
                
            get_divition_list:null,
            get_team_list:null,
            get_employee_list:null,
            get_employee_team:null,
 
            product_id:null,
            job_id:null,
            get_product_list:[],
            get_job_list:['LEAD','JIH-TRADING','JIH-FITOUT','JIH-PROJECT','JIH-MAINTENANCE','TENDER'],
          

            total_payment_summary: {},
            total_realization_summary: {},
            
            getorderbooking: { total_target: 0, total_achieved: 0, total_achieved_others: 0, percentage: 0 },
            getorderrevenue: { total_target: 0, total_achieved: 0, percentage: 0 },
            get_quote_submitted: { total_expected_revenue: 0, lead_count: 0 },
            get_probability_values: [],
            get_activity_value: { done_today: 0, planning_today: 0, done_month: 0, planning_month: 0 },
            get_employee_payment_totals: {},
            new_get_employee_payment_totals: { summary: [] },
            get_realization_summary: [],
            
            get_mail_activity_lists: { formatted_activities: [] },

            get_quote_graph_company:{
                                      tag_name:[],
                                      revenue:[],
                                      total_leads:[]
                                     },
             get_won_graph_company:{
                                      tag_name:[],
                                      revenue:[],
                                      total_leads:[]
                                     },
            get_quote_graph_product:{ product:[],
                                      revenue:[],
                                      total_leads:[]
                                    },
            get_forecast_graph_company:{
                                      tag_name:[],
                                      revenue:[],
                                      total_leads:[]},
            get_forecast_graph_product:{
                                    product:[],
                                    revenue:[],
                                    total_leads:[]
                                          }
            

        })
        onWillStart(async () => {
            this.state.userId=user.userId
            try {
                const currName = await this.orm.call('crm.lead', 'get_company_currency', [], {
                    comp_id: this.state.comp_id || false,
                });
                if (currName) {
                    this.state.currency_name = currName;
                }
            } catch (err) {
                console.error("Could not fetch company currency name:", err);
            }
            this.state.isAdmin = await user.hasGroup("base.group_system");
            this.state.account_admin = await user.hasGroup("base.group_system");
            this.state.isTeamLead = await user.hasGroup("crm_dashboard.dashboard_team_leader");
            if (this.state.isTeamLead){
                 this.state.isAdmin=true
                 await this.getTeamLeadAccess();
            }
            await this.get_employee_list()
           await this.get_team_list()
           await this.get_divition_list();
             if (!this.state.isAdmin){
                this.state.user_id=this.state.userId
                this.get_employee_changes()
            }

           
         

            // Restore filters if available
            const savedFilters = sessionStorage.getItem("crm_filters");
            if (savedFilters) {
                this.state.filters = JSON.parse(savedFilters);
                console.log("this is my filter selection ", this.state.filters)
                if (this.state.filters){
                     if (this.state.filters.team_id){
                         this.state.team_id=this.state.filters.team_id
                        }
                     if (this.state.filters.comp_id){
                         this.state.comp_id=this.state.filters.comp_id
                        }
                     if (this.state.filters.user_id){
                         this.state.user_id=this.state.filters.user_id
                        }
                     if (this.state.filters.product_id){
                         this.state.product_id=this.state.filters.product_id
                        }
                     if (this.state.filters.job_id){
                         this.state.job_id=this.state.filters.job_id
                        }
                    if (this.state.filters.select_month){
                         this.state.select_month=this.state.filters.select_month
                        }
                    if (this.state.filters.filterLists){
                         this.state.filterLists=this.state.filters.filterLists
                        }
                }
            }

            if (this.state.comp_id || this.state.product_id){
                this.render_dashboard_methods()
                 this.get_product_list()
            }

           await loadJS('https://cdn.tailwindcss.com')
           await loadJS("https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js")
           await this.setOverflow()
           // await this.get_product_list()
         

           await this.getorderbooking()
           await this.getorderrevenue()
           await this.get_quote_submitted()
           await this.get_probability_values()
           await this.get_employee_payment_totals()
           // await this.new_get_employee_payment_totals()
           // await this.get_realization_summary()
           await this.get_mail_activity_values()
           await this.get_activity_value()
           await this.get_quote_submitted_graph_company()
           await this.get_won_stage_graph_company()
           await this.get_forecast_submitted_graph_company()
           await this.render_dashboards();
           this.state.select_month_forecast = this.state.forecastmonth_list.length > 0 ? this.state.current_month : 0 

             console.log("this is my state values ", this.state)
   

        })

        onMounted(async () => {
            console.log('Component mounted, ----------------------------------------------->');
            this.getquotecompanywisegraph();
            this.getwoncompanywisegraph();
            this.getquoteproductwisegraph();
            this.getforecastcompanywisegraph();
            this.getforecastproductwisegraph();
            this.setDropdownSelections();
            
           console.log("this is my state values ", this.state)

            const savedSection = sessionStorage.getItem('current_view');
              if (savedSection) {
                document.getElementById(savedSection)?.scrollIntoView({ behavior: 'smooth' });
              }
             sessionStorage.setItem('current_view', null);  


            console.log('Component mounted completed ----------------------------------------------->');
        });

       
    }

    setOverflow = async () => {
        let data = document.getElementsByClassName('o_action_manager');
        console.log("this is the data of element", data);
        if (data.length > 0) {
            data[0].classList.add("custom_overflow"); // Add a new class
        }
    };

    toggleFilter=()=> {
        this.state.isFilterHidden = !this.state.isFilterHidden;
        console.log("this is my toggle ", this.state.isFilterHidden)
    }


    setfiltercolor =async(box,type)=>{
            if (box && type){
                console.log("this is my box and type",box,type)
                if (box == 'b1'){
                    this.state.filter_by.b1 = type
                    this.get_quote_submitted();
                }
                else if (box == 'b2'){
                    this.state.filter_by.b2 = type
                    this.get_quote_submitted_graph_company();
                    setTimeout(()=>{
                    this.getquotecompanywisegraph()
                    },600)
                    if(this.state.comp_id){
                        this.get_quote_submitted_graph_product();
                        setTimeout(()=>{
                        this.getquoteproductwisegraph()
                        },600)
                    }
                }
                else if (box == 'b3'){
                    this.state.filter_by.b3 = type
                    this.get_forecast_submitted_graph_company();
                    setTimeout(()=>{
                        this.getforecastcompanywisegraph()
                    },600)
                   
                    if(this.state.comp_id){
                        this.get_forecast_submitted_graph_product();
                        setTimeout(()=>{
                            this.getforecastproductwisegraph()
                        },600)
                       
                    }
                }
                else if (box == 'b4'){
                    this.state.filter_by.b4 = type
                    this.get_probability_values()
                }
                 else if (box == 'b5'){
                    this.state.filter_by.b5 = type
                    this.get_won_stage_graph_company();
                    setTimeout(()=>{
                        this.getwoncompanywisegraph()
                    },600)
                   
                }
                

                console.log("this is my sel filter ",this.state.filter_by)
            }


    }



    setDropdownSelections = () =>{
            const dropdowns = [
              
                this.state.select_month ? { selector: ".month-selector", value: this.state.select_month } : null,
                this.state.select_month_revenue ? { selector: ".month-selector-revenue", value: this.state.select_month_revenue } : null,
                this.state.new_select_month ? { selector: ".new-month-selector", value: this.state.new_select_month } : null,
                this.state.select_month_forecast ? { selector: ".month-selector-forecast", value: this.state.select_month_forecast } : null,

                
                
              
            ].filter(Boolean); // Removes `false`, `null`, `undefined`, `0`, `""`, `NaN`

            dropdowns.forEach(({ selector, value }) => {
                const dropdown = document.querySelector(selector);
                if (dropdown) {
                    dropdown.value = value;
                }
            });
            const selected_list = [
                this.state.comp_id ? { selector: "selected_company_id", value: parseInt(this.state.comp_id)} : null,
                this.state.product_id ? { selector: "selected_product_id", value: parseInt(this.state.product_id) } : null,
                this.state.job_id ? { selector: "selected_job_id", value: this.state.job_id } : null,
                this.state.team_id ? { selector: "selected_team_id", value: parseInt(this.state.team_id) } : null,
                this.state.user_id ? { selector: "selected_employee_id", value: parseInt(this.state.user_id) } : null,
                ].filter(Boolean);
         selected_list.forEach(({ selector, value }) => {
             this.state[selector] = value
         });
        
         // Handle the filters in reverse order]
        console.log("this is our filterLists ************************************************************",this.state.filterLists)
        if (this.state.filterLists?.length > 0) {
                this.state.filterLists.map((filter) => {
                    console.log("Processing filter =>", filter);
            
                    switch (filter) {
                        case 'company':
                            if (this.state.comp_id) {
                                this.get_company_changes();
                                console.log("Processing filter company =>", filter,this.state.comp_id)
                            }
                            break;
                        case 'team':
                            if (this.state.team_id) {
                                this.get_team_changes();
                                console.log("Processing filter team =>", filter,this.state.team_id)
                            }
                            break;
                        case 'employee':
                            if (this.state.user_id) {
                                this.get_employee_changes();
                                console.log("Processing filter employee =>", filter,this.state.user_id)
                            }
                            break;
                        default:
                            console.log("Unknown filter:", filter);
                    }
                });
            }
       
       
        
        }


        // updateFilterList = async(newFilter)=> {
        //     // Remove if it already exists
        //     if (this.state.filterLists){
        //         const index = this.state.filterLists.indexOf(newFilter);
        //         if (index !== -1) {
        //             this.state.filterLists.splice(index, 1);
        //         }
        //     }
            
        //     // Add to the front
        //     this.state.filterLists.unshift(newFilter);

        //     console.log("this is my state for the update list ", this.state.filterLists)
        
           
        // }

            updateFilterList = async (newFilter) => {
            // Remove if it already exists
            if (this.state.filterLists) {
                const index = this.state.filterLists.indexOf(newFilter);
                if (index !== -1) {
                    this.state.filterLists.splice(index, 1);
                }
            }
        
            // Add to the end (old to new order)
            this.state.filterLists.push(newFilter);
        
            console.log("this is my state for the update list ", this.state.filterLists);
            }


          reset_dashboard_filter = async()=>{

               sessionStorage.setItem("crm_filters", JSON.stringify({}))
                let dropdowns = [{ selector: ".company-selector", value:0},
                                   { selector: ".team-selector", value:0},
                                   { selector: ".user-selector", value:0},
                                   { selector: ".job-selector", value:0},
                                   { selector: ".product-selector", value:0},
                                  { selector: ".company-selector1", value:0},
                                   { selector: ".team-selector1", value:0},
                                   { selector: ".user-selector1", value:0},
                                   { selector: ".job-selector1", value:0},
                                   { selector: ".product-selector1", value:0}]
              if (this.state.isAdmin){
                     if (!this.state.isTeamLead){
                           dropdowns.push({ selector: ".month-selector", value:0})
                           dropdowns.push({ selector: ".new-month-selector", value:0})
                          
                        
                     }
              }
              
               dropdowns.push({ selector: ".month-selector-forecast", value :this.state.forecastmonth_list.length > 0 ? this.state.current_month : 0 })
               dropdowns.push({ selector: ".month-selector-revenue", value:0})
        

                dropdowns.forEach(({ selector, value }) => {
                const dropdown = document.querySelector(selector);
                if (dropdown) {
                    dropdown.value = value;
                }
            });
                                   
               this.state.team_id=null
               this.state.comp_id=null
               this.state.user_id=null
               this.state.product_id=null
               this.state.job_id=null
      

                this.state.selected_company_id=0
                 this.state.selected_product_id=0
                 this.state.selected_job_id=0
                 this.state.selected_team_id=0
                 this.state.selected_employee_id=0
                 this.state.select_month_revenue=0
                 this.state.select_month_forecast=this.state.forecastmonth_list.length > 0 ? this.state.current_month : 0 
                 this.state.forecast_load=true
                 this.state.get_product_list=[]
             
                
              
              

               await this.get_employee_list()
               await this.get_team_list()
               await this.get_divition_list();
                if (!this.state.isAdmin){
                this.state.user_id=this.state.userId
                this.get_employee_changes()
            }
               
               await this.getorderbooking()
               await this.getorderrevenue()
               await this.get_quote_submitted()
               await this.get_probability_values()
               await this.get_mail_activity_values()
               await this.get_activity_value()
               await this.get_employee_payment_totals()
               // await this.new_get_employee_payment_totals()
               // await this.get_realization_summary()
               // await this.get_realization_summary()
               await this.render_dashboard_methods()
               await this.render_dashboards();
             
        
    }
    


    calling_methods = async()=>{
        await this.getorderbooking()
        await this.getorderrevenue()
        await this.get_quote_submitted()
        await this.get_probability_values()
        await this.get_mail_activity_values()
        await this.get_activity_value()
        await this.get_employee_payment_totals()
        // await this.new_get_employee_payment_totals()
        // await this.get_realization_summary()

        setTimeout(()=>{
             console.log("this is my state values ", this.state)
        },2000)
    }





    onchange_company = (event) => {
        console.log("Event object:", event);
      
        if (event && event.target) {
            let value = event.target.value;
    
            if (value > 0) {
                if (value != this.state.comp_id) {
                    this.state.forecast_load=true
                    this.state.comp_id = value;
                    
                    // this.state.product_id=null
                    this.get_product_list()
                    this.get_company_changes()
         
                    this.updateFilterList('company');
                    this.calling_methods()
                    this.render_dashboard_methods()
                    this.state.selected_company_id=parseInt(value)
               
                    // this.get_company_employee()

                    
                    
                }
            }
            else{
                console.log("this is else of set default comp",value)
                this.state.comp_id=null
                this.state.product_id=null
               
                this.state.product_list=[]
                this.state.forecast_load=true
                this.state.get_product_list=[]
                
                this.get_company_changes()
                this.get_employee_changes()
                this.calling_methods()
                this.render_dashboard_methods()
            
                this.state.selected_company_id=parseInt(value)
              
                // this.get_product_list()
                

            }
        }
        
    };


 

     onchange_Product = (event) => {
        console.log("Event object:", event);
    
        if (event && event.target) {
            let value = event.target.value;
            this.state.selected_product_id=parseInt(value)
            if (value > 0) {
                if (value != this.state.product_id) {
                    this.state.forecast_load=true
                   
                    this.state.product_id = value;
                    this.updateFilterList('product');
                     this.calling_methods()
                    this.render_dashboard_methods()
                 
                    
                }
            }
            else{
                console.log("this is else of set default product",value)
                this.state.product_id=null
                
                this.state.forecast_load=true
                this.calling_methods()
                this.render_dashboard_methods()
        

            }
        }
    };
    onchange_revenue_month=(event)=>{
         console.log("Month object:", event);
         if (event && event.target) {
             
            let value = event.target.value;
             
            if (value != 0 ){
                if (value) {
                    if (value != this.state.select_month_revenue) {
                        console.log("this is my select_month_revenue selection",value)
                         this.state.select_month_revenue=value
                         this.calling_methods()
                    }
                }
            }
             else{
                 console.log("this is my  select_month_revenue selection")
                 this.state.select_month_revenue=null
                 this.calling_methods()
             }
         }
                                     
    }


     onchange_forecast_month= (event)=>{
         console.log("Month object:", event);
         if (event && event.target) {
             
            let value = event.target.value;
             
            if (value != 0 ){
                if (value) {
                    if (value != this.state.select_month_forecast) {
                        console.log("this is my select_month_revenue selection",value)
                         this.state.select_month_forecast=value
                         this.render_dashboard_methods()
  
                    }
                }
            }
             else{
                 console.log("this is my  select_month_revenue selection")
                 this.state.select_month_forecast=null
                 this.get_forecast_submitted_graph_company()
                 this.render_dashboard_methods()

                 
             }
         }
                                     
    }

    onchange_payment_month = (event)=>{
          console.log("Month object:", event);
         if (event && event.target) {
             
            let value = event.target.value;
             
            if (value != 0 ){
                if (value) {
                    if (value != this.state.select_month) {
                        console.log("this is my month selection",value)
                         this.state.select_month=value
                         this.calling_methods()
                    }
                }
            }
             else{
                 console.log("this is my  0 month selection")
                 this.state.select_month=null
                 this.calling_methods()
             }
         }
    }


      new_onchange_payment_month = (event)=>{
          console.log("Month object:", event);
         if (event && event.target) {
             
            let value = event.target.value;
             
            if (value != 0 ){
                if (value) {
                    if (value != this.state.new_select_month) {
                        console.log("this is my month selection",value)
                         this.state.new_select_month=value
                         this.calling_methods()
                    }
                }
            }
             else{
                 console.log("this is my  0 month selection")
                 this.state.new_select_month=null
                 this.calling_methods()
             }
         }
    }


    onchange_Job = (event) => {
        console.log("Event object:", event);
    
        if (event && event.target) {
            let value = event.target.value;
            this.state.selected_job_id=value
            if (value) {
                if (value != this.state.job_id) {
                   
                   this.state.get_employee_list
                   this.state.job_id = value;
                   this.updateFilterList('job');
                    this.state.forecast_load=true
                    this.calling_methods()
                    this.render_dashboard_methods()
                   
                    
                }
            }
            else{
                console.log("this is else of set default Job",value)
                
                this.state.forecast_load=true
                this.state.job_id=null
                this.calling_methods()
                this.render_dashboard_methods()
               
                

            }
        }
    };

    
    onchange_team = (event) => {
        console.log("Event object team:", event);
    
        if (event && event.target) {
            let value = event.target.value;
            this.state.selected_team_id=parseInt(value)
            if (value > 0) {
                if (value != this.state.team_id) {
                    
                    this.state.team_id = value;
                    // this.state.user_id=null
                    this.state.forecast_load=true
                    this.get_employee_team()
                    this.get_team_changes()
                    this.calling_methods()  
                    this.render_dashboard_methods()  
                    this.updateFilterList('team');
                  
                }
            }
            else{
                console.log("this is else of set default comp",value)
                this.state.team_id = null;
              
                this.get_team_changes()
                this.state.forecast_load=true
           
                this.get_company_changes()
                this.get_employee_list();
                this.get_employee_changes()
                this.calling_methods()
                this.render_dashboard_methods()
                // this.state.select_month_forecast=this.state.forecastmonth_list.length > 0 ? this.state.current_month : null;
                // this.setDropdownSelections();

              

                
            }
        }
        
    };



    onchange_employee = (event) => {
        console.log("Event object Employee:", event);
       
        if (event && event.target) {
            let value = event.target.value;
            this.state.selected_employee_id=parseInt(value)
            if (value > 0) {
                if (value != this.state.user_id) {
                  
                    this.state.forecast_load=true
                    this.state.user_id = value;
                    this.get_employee_changes()
                    this.calling_methods()
                    this.render_dashboard_methods()
                    this.updateFilterList('employee');
                 
                }
            }
            else{
                this.state.user_id=null
               
                this.state.forecast_load=true
                this.get_employee_changes()
                this.get_company_changes() 
                this.get_employee_list()
                this.calling_methods()
                this.render_dashboard_methods()
               
            }
        }
        
    };

    getTeamLeadAccess =async()=>{
        try{
            const result = await rpc('/web/dataset/call_kw', {
                model: 'crm.lead',
                method: 'get_team_lead_access',
                args: [[]], 
                kwargs: {
                    user_id:this.state.userId
                },
            });
            console.log("get_team_lead_access",result)
            result.team_list.sort((a, b) => a.name.toLowerCase().localeCompare(b.name.toLowerCase()));
            result.company_list.sort((a, b) => a.name.toLowerCase().localeCompare(b.name.toLowerCase()));
            result.employee_list.sort((a, b) => a.name.toLowerCase().localeCompare(b.name.toLowerCase()));
            this.state.get_team_list=result.team_list
            this.state.get_employee_list= result.employee_list
             this.state.get_divition_list= result.company_list
            
           
     
           
        }
        catch{
    
          console.error("the error in get_team_lead_access")
        }
        
    }
     


   
    get_divition_list=async()=>{
        try{
            if (!this.state.isTeamLead){
            const result = await rpc('/web/dataset/call_kw', {
                model: 'crm.lead',
                method: 'get_divition_list',
                args: [[]], 
                kwargs: {},
            });
            console.log("get_divition_list",result)
            result.sort((a, b) => a.name.toLowerCase().localeCompare(b.name.toLowerCase()));
            this.state.get_divition_list=result
           

            if (this.state.comp_id){
                let company=this.state.get_divition_list.some((comp)=>{
                    return comp.id == this.state.comp_id
                })
                if (!company){
                    this.state.comp_id=null
                }
            }
                    
            } 
        }
        catch{
    
          console.error("the error in get_divition_list")
        }
    }

    get_employee_list=async()=>{
        try{
            if (!this.state.isTeamLead){
            const result = await rpc('/web/dataset/call_kw', {
                model: 'crm.lead',
                method: 'get_employee_list',
                args: [[]], 
                kwargs: {},
            });
            console.log("get_employee_list",result)
            
            result.sort((a, b) => a.name.toLowerCase().localeCompare(b.name.toLowerCase()));

            this.state.get_employee_list=result

            
            if (this.state.user_id){
                let user=this.state.get_employee_list.some((emp)=>{
                    return emp.id == this.state.user_id
                })
                if (!user){
                    this.state.user_id=null
                }
            }

        
            }  
        }
        catch{
    
          console.error("the error in get_employee_list")
        }
    }

    get_product_list = async () => {
        try {
            const result = await this.orm.call('crm.lead', 'get_product_list', [], {
                divition: this.state.comp_id || false,
            });
            
            console.log("get_product_list", result);
            if (result && Array.isArray(result)) {
                result.sort((a, b) => (a.name || '').toLowerCase().localeCompare((b.name || '').toLowerCase()));
                this.state.get_product_list = result;
            } else {
                this.state.get_product_list = [];
            }

            if (this.state.product_id) {
                let product = this.state.get_product_list.some((pro) => {
                    return pro.id == this.state.product_id;
                });
                if (!product) {
                    this.state.product_id = null;
                }
            }
        } catch (err) {
            console.error("the error in get_product_list", err);
        }
    }


    get_team_list=async()=>{
       
        try{
             if (!this.state.isTeamLead){
            const result = await rpc('/web/dataset/call_kw', {
                model: 'crm.lead',
                method: 'get_team_list',
                args: [[]], 
                kwargs: {},
            });
            console.log("get_team_list",result)
            result.sort((a, b) => a.name.toLowerCase().localeCompare(b.name.toLowerCase()));
            this.state.get_team_list=result

            if (this.state.team_id){
                let team=this.state.get_team_list.some((team)=>{
                    return team.id == this.state.team_id
                })
                if (!team){
                    this.state.team_id=null
                }
            }
             }
        }
        catch{
    
          console.error("the error in get_team_list")
        }
    }


    get_employee_team=async()=>{
        try{
            const result = await rpc('/web/dataset/call_kw', {
                model: 'crm.lead',
                method: 'get_employee_team',
                args: [[]], 
                kwargs: {
                    crm_team_id:this.state.team_id
                },
            });
            console.log("get_employee_team",result)
            result.sort((a, b) => a.name.toLowerCase().localeCompare(b.name.toLowerCase()));
            this.state.get_employee_list=result

              if (this.state.user_id){
                let emp=this.state.get_employee_list.some((emp)=>{
                    return emp.id == this.state.user_id
                })
                if (!emp){
                    this.state.user_id=null
                }
            }
           
        }
        catch{
    
          console.error("the error in get_employee_team")
        }
    }

    get_team_changes=async()=>{
        try{
            const result = await rpc('/web/dataset/call_kw', {
                model: 'crm.lead',
                method: 'get_team_changes',
                args: [[]], 
                kwargs: {
                    team_id:this.state.team_id
                },
            });
            console.log("get_team_changes",result)

            this.state.get_divition_list=result

             if (this.state.comp_id){
                let company=this.state.get_divition_list.some((comp)=>{
                    return comp.id == this.state.comp_id
                })
                if (!company){
                    this.state.comp_id=null
                }
            }
                
        
           
        }
        catch{
    
          console.error("the error in get_team_changes")
        }
    }


    get_employee_changes =async()=>{
        try{
             if (!this.state.isTeamLead){
            const result = await rpc('/web/dataset/call_kw', {
                model: 'crm.lead',
                method: 'get_employee_changes',
                args: [[]], 
                kwargs: {
                    emp_id:this.state.user_id,
                    
                },
            });
            const seen = new Set();
            const uniqueItems = [];
            console.log("get_employee_changes",result)
            result.comp_lists.forEach(item => {
              const key = `${item.id}-${item.name}`; // Combine id and name as key
              if (!seen.has(key)) {
                seen.add(key);
                uniqueItems.push({ id: item.id, name: item.name });
              }
            });
            if (!this.state.selected_team_id){  
                this.state.get_divition_list=uniqueItems
            }
            this.state.get_team_list=result.team_list


             if (this.state.comp_id){
                let company=this.state.get_divition_list.some((comp)=>{
                    return comp.id == this.state.comp_id
                })
                if (!company){
                    this.state.comp_id=null
                }
            }

             if (this.state.team_id){
                let team=this.state.get_team_list.some((team)=>{
                    return team.id == this.state.team_id
                })
                if (!team){
                    this.state.team_id=null
                }
            }
                
             }
           
        }
        catch{
    
          console.error("the error in get_employee_changes")
        }
    }



        get_company_changes=async()=>{
        try{
            const currName = await this.orm.call('crm.lead', 'get_company_currency', [], {
                comp_id: this.state.comp_id || false,
            });
            if (currName) {
                this.state.currency_name = currName;
            }
              if (!this.state.isTeamLead){
            const result = await rpc('/web/dataset/call_kw', {
                model: 'crm.lead',
                method: 'get_company_changes',
                args: [[]], 
                kwargs: {
                    comp_id:this.state.comp_id
                },
            });
            console.log("get_company_changes",result)
            this.state.get_team_list=[]
            this.state.get_employee_list=[]
            this.state.get_team_list=result.team_lists
            this.state.get_employee_list=result.team_members


                if (this.state.user_id){
                let emp=this.state.get_employee_list.some((emp)=>{
                    return emp.id == this.state.user_id
                })
                if (!emp){
                    this.state.user_id=null
                }
            }


                if (this.state.team_id){
                let team=this.state.get_team_list.some((team)=>{
                    return team.id == this.state.team_id
                })
                if (!team){
                    this.state.team_id=null
                }
            }
           

              }
            
           
        }
        catch{
    
          console.error("the error in get_company_changes")
        }
    }


    // get_company_employee=async()=>{
    //     try{
    //         const result = await rpc('/web/dataset/call_kw', {
    //             model: 'crm.lead',
    //             method: 'get_company_employee',
    //             args: [[]], 
    //             kwargs: {
    //                 comp_id:this.state.comp_id
    //             },
    //         });
    //         console.log("get_company_employee",result)

    //         this.state.get_employee_list=result
           
    //     }
    //     catch{
    
    //       console.error("the error in get_company_employee")
    //     }
    // }



    




    getorderbooking=async()=>{
        try{
            const result = await rpc('/web/dataset/call_kw', {
                model: 'crm.lead',
                method: 'get_employee_order_booking_target_and_achieved',
                args: [[]], 
                kwargs: {
                    comp_id:this.state.comp_id,
                    team_id:this.state.team_id,
                    user_id:this.state.user_id,
                    product_id:this.state.product_id,
                    job_id:this.state.job_id,
                    month_name:this.state.select_month_revenue
                },
            });
            console.log("getorderbooking--------------------------------->",result)

            this.state.getorderbooking = result || { total_target: 0, total_achieved: 0, total_achieved_others: 0, percentage: 0 };
           
        }
        catch{
          this.state.getorderbooking = { total_target: 0, total_achieved: 0, total_achieved_others: 0, percentage: 0 };
          console.error("the error in getorderbooking")
        }
    }

    getorderrevenue=async()=>{
        try{
            const result = await rpc('/web/dataset/call_kw', {
                model: 'crm.lead',
                method: 'get_employee_invoice_target_and_achieved',
                args: [[]], 
                kwargs: {
                    comp_id:this.state.comp_id,
                    team_id:this.state.team_id,
                    user_id:this.state.user_id,
                    month_name:this.state.select_month_revenue
                },
            });
            console.log("getorderrevenue",result)

            this.state.getorderrevenue = result || { total_target: 0, total_achieved: 0, percentage: 0 };
           
        }
        catch{
          this.state.getorderrevenue = { total_target: 0, total_achieved: 0, percentage: 0 };
          console.error("the error in getorderrevenue")
        }
    }

    get_quote_submitted=async()=>{
        try{
            const result = await rpc('/web/dataset/call_kw', {
                model: 'crm.lead',
                method: 'get_quote_submitted',
                args: [[]], 
                kwargs: {
                    comp_id:this.state.comp_id,
                    team_id:this.state.team_id,
                    user_id:this.state.user_id,
                    product_id:this.state.product_id,
                    job_id:this.state.job_id,
                    filter_by:this.state.filter_by.b1
                },
            });
            console.log("get_quote_submitted",result)

            this.state.get_quote_submitted = result || { total_expected_revenue: 0, lead_count: 0 };
           
        }
        catch{
    
          console.error("the error in get_quote_submitted")
        }
    }



    get_probability_values=async()=>{
        try{
            const result = await rpc('/web/dataset/call_kw', {
                model: 'crm.lead',
                method: 'get_probability_values',
                args: [[]], 
                kwargs: {
                    comp_id:this.state.comp_id,
                    team_id:this.state.team_id,
                    user_id:this.state.user_id,
                    product_id:this.state.product_id,
                    job_id:this.state.job_id,
                    filter_by:this.state.filter_by.b4
                },
            });
            console.log("get_probability_values",result)

            this.state.get_probability_values=result
           
        }
        catch{
    
          console.error("the error in get_probability_values")
        }
    }



    get_mail_activity_values=async()=>{
        try{
            const result = await rpc('/web/dataset/call_kw', {
                model: 'crm.lead',
                method: 'get_mail_activity_lists',
                args: [[]], 
                kwargs: {
                    user_id:this.state.user_id,
                    comp_id:this.state.comp_id,
                    team_id:this.state.team_id,
                    // filter_by:this.state.filter_by.b4
                },
            });
            console.log("get_mail_activity_lists",result)

            this.state.get_mail_activity_lists=result
           
        }
        catch{
    
          console.error("the error in get_mail_activity_lists")
        }
    }

    get_employee_payment_totals=async()=>{
        try{
            const result = await rpc('/web/dataset/call_kw', {
                model: 'crm.lead',
                method: 'get_employee_payment_totals',
                args: [[]], 
                kwargs: {
                    comp_id:this.state.comp_id,
                    team_id:this.state.team_id,
                    user_id:this.state.user_id,
                    month_name:this.state.select_month
                    // product_id:this.state.product_id,
                    // job_id:this.state.job_id,
                    
                },
            });
            console.log("get_employee_payment_totals -------------------------------  values",result)


            this.state.get_employee_payment_totals=result
           
        }
        catch{
    
          console.error("the error in get_employee_payment_totals values")
        }
    }


    new_get_employee_payment_totals=async()=>{
        try{
            const result = await rpc('/web/dataset/call_kw', {
                model: 'crm.lead',
                method: 'new_get_employee_payment_totals',
                args: [[]], 
                kwargs: {
                    comp_id:this.state.comp_id,
                    team_id:this.state.team_id,
                    user_id:this.state.user_id,
                    month_name:this.state.new_select_month
                    // product_id:this.state.product_id,
                    // job_id:this.state.job_id,
                    
                },
            });
            console.log("new_get_employee_payment_totals -------------------------------  values",result)

            if(result == null){
                 this.state.new_get_employee_payment_totals=[]
            }
            else{
                
            this.state.new_get_employee_payment_totals=result
            await this.formatTotalSummaryRow();
            }
           
        }
        catch{
    
          console.error("the error in new_get_employee_payment_totals values")
        }
    }   

  get_realization_summary=async()=>{
        try{
            const result = await rpc('/web/dataset/call_kw', {
                model: 'crm.lead',
                method: 'get_realization_summary',
                args: [[]], 
                kwargs: {
                    comp_id:this.state.comp_id,
                    team_id:this.state.team_id,
                    user_id:this.state.user_id,
                },
            });
            console.log("get_realization_summary -------------------------------  values",result)
           
            if(result == null){
                 this.state.get_realization_summary=[]
                 this.state.get_realization_summary_domain=[]
            }
            else{  
            this.state.get_realization_summary=result.result
            this.state.get_realization_summary_domain=result.onclick_domain
            await this.realizationTotalRow()
            }
           
        }
        catch{
    
          console.error("the error in get_realization_summary values")
        }
    } 





    get_activity_value=async()=>{
        try{
            const result = await rpc('/web/dataset/call_kw', {
                model: 'crm.lead',
                method: 'get_activity',
                args: [], 
                kwargs: {
                    comp_id:this.state.comp_id,
                    team_id:this.state.team_id,
                    user_id:this.state.user_id,
                    // product_id:this.state.product_id,
                    // job_id:this.state.job_id,
                    
                },
            });
            console.log("get_activity values",result)


            this.state.get_activity_value=result
           
        }
        catch{
    
          console.error("the error in get_activity values")
        }
    }



    render_dashboards = async()=>{
        this.getwoncompanywisegraph()
        this.getquotecompanywisegraph()
        this.getforecastcompanywisegraph()
         if (this.state.comp_id){
             this.getquoteproductwisegraph()
             this.getforecastproductwisegraph()
         }
        
       
        
    }


    render_dashboard_methods = async()=>{
        await this.get_quote_submitted_graph_company();
        await this.get_won_stage_graph_company();
        await this.get_forecast_submitted_graph_company();
        setTimeout(()=>{
        
         this.getquotecompanywisegraph()
          this.getwoncompanywisegraph()  
         this.getforecastcompanywisegraph();
             
        },600)
        if (this.state.comp_id || this.state.product_id || this.state.job_id ){
            this.get_quote_submitted_graph_product();
            this.get_forecast_submitted_graph_product();
            setTimeout(()=>{
                 this.getquoteproductwisegraph();
                this.getforecastproductwisegraph();
               
                },800)
           
        }
      
    }


    get_quote_submitted_graph_company =async()=>{
        try{
            const result = await rpc('/web/dataset/call_kw', {
                model: 'crm.lead',
                method: 'get_quote_submitted_graph_company',
                args: [[]], 
                kwargs: {
                     comp_id:this.state.comp_id,
                    team_id:this.state.team_id,
                    user_id:this.state.user_id,
                    // product_id:this.state.product_id,
                    job_id:this.state.job_id,
                    filter_by:this.state.filter_by.b2
                },
            });

            this.state.get_quote_graph_company=result
         
        }
        catch{
    
          console.error("the error in get_quote_submitted_graph values")
        }
    }



        get_won_stage_graph_company =async()=>{
        try{
            const result = await rpc('/web/dataset/call_kw', {
                model: 'crm.lead',
                method: 'get_won_stage_graph_company',
                args: [[]], 
                kwargs: {
                     comp_id:this.state.comp_id,
                    team_id:this.state.team_id,
                    user_id:this.state.user_id,
                    // product_id:this.state.product_id,
                    job_id:this.state.job_id,
                    filter_by:this.state.filter_by.b5
                },
            });

            this.state.get_won_graph_company=result
            console.log("this is my won stage graph detals ",result)
          
         
        }
        catch{
    
          console.error("the error in get_won_submitted_graph values")
        }
    }


    get_quote_submitted_graph_product =async()=>{
        try{
            const result = await rpc('/web/dataset/call_kw', {
                model: 'crm.lead',
                method: 'get_quote_submitted_graph_product',
                args: [[]], 
                kwargs: {
                    comp_id:this.state.comp_id,
                    team_id:this.state.team_id,
                    user_id:this.state.user_id,
                    product_id:this.state.product_id,
                    job_id:this.state.job_id,
                    filter_by:this.state.filter_by.b2
                },
            });

            this.state.get_quote_graph_product=result
        
        }
        catch{
    
          console.error("the error in get_quote_submitted_graph_product values")
        }
    }

    get_forecast_submitted_graph_company =async()=>{
        try{
            const result = await rpc('/web/dataset/call_kw', {
                model: 'crm.lead',
                method: 'get_forecast_submitted_graph_company',
                args: [[]], 
                kwargs: {
                    comp_id:this.state.comp_id,
                    team_id:this.state.team_id,
                    user_id:this.state.user_id,
                    
                    job_id:this.state.job_id,
                    filter_by:this.state.filter_by.b3,
                    month_name:this.state.select_month_forecast,

                },
            });

            this.state.get_forecast_graph_company=result
           
          
            if (this.state.forecast_load){  
                 const available_months =result.available_months
                 this.state.forecastmonth_list = this.state.month_list.filter(month =>
                        available_months.includes(month.id)
                    );
                this.state.forecast_load=false
                this.state.select_month_forecast=this.state.forecastmonth_list.length > 0 ? this.state.current_month : null;
                setTimeout(()=>{
                      this.setDropdownSelections();
                },3000);
              
                
            }
             console.log("this is my forecast list from the forecastgraph method  ===============================&&&&&&",this.state.forecast_load,this.state.forecastmonth_list)
         
        }
        catch{
    
          console.error("the error in get_forecast_submitted_graph_company values")
        }
    }



    get_forecast_submitted_graph_product =async()=>{
        try{
            
            const result = await rpc('/web/dataset/call_kw', {
                model: 'crm.lead',
                method: 'get_forecast_submitted_graph_product',
                args: [[]], 
                kwargs: {
                    comp_id:this.state.comp_id,
                    team_id:this.state.team_id,
                    user_id:this.state.user_id,
                    product_id:this.state.product_id,
                    job_id:this.state.job_id,
                    filter_by:this.state.filter_by.b3,
                    month_name:this.state.select_month_forecast,
                },
            });

            this.state.get_forecast_graph_product=result
            console.log("this is my returned month for the forecats product",this.state.select_month_forecast)
                
            
        
        }
        catch{
    
          console.error("the error in get_forecast_submitted_graph_product values")
        }
    }




    

     getquoteproductwisegraph_pie = ()=>{
        if (this.chartQuoteProduct) {
            this.chartQuoteProduct.destroy();  // Destroy the old chart instance
        }
       

        
        const data = {
            labels: this.state.get_quote_graph_product.product ,
            datasets: [
                {
                    label:'Revenue',
                    data:this.state.get_quote_graph_product.revenue,
                    backgroundColor: ["#3e6a8f","#f09f5f","#8d629d","#d2aca3","#cacdcf","#eec8a5","#3e2cfdc","#72c4af"],
                  }
                  ,{
                    label: 'Total Leads',
                    data: this.state.get_quote_graph_product.total_leads,
                    backgroundColor: ["#3e6a8f","#f09f5f","#8d629d","#d2aca3","#cacdcf","#eec8a5","#3e2cfdc","#72c4af"],
                  }
            ]
          };


        if (this.chartRefQuoteProduct && this.chartRefQuoteProduct.el) {
            this.chartQuoteProduct = new Chart(this.chartRefQuoteProduct.el, {
                type: 'pie',
                data: data,
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            display:false
                        },
                        title: {
                            display: false,
                           
                        }
                        }
                },
            });
            let id='legend2'
            this.createCustomLegend(data,id);
        }

    }





    getquotecompanywisegraph_pie = ()=>{
        if (this.chartQuoteCompany) {
            this.chartQuoteCompany.destroy();  // Destroy the old chart instance
        }
       

        const data = {
            labels: this.state.get_quote_graph_company.tag_name,
            datasets: [
              {
                label:'Revenue',
                data:this.state.get_quote_graph_company.revenue,
                backgroundColor: ["#3e6a8f","#f09f5f","#8d629d","#d2aca3","#cacdcf","#eec8a5","#75aede","#72c4af"],
              }
              ,{
                label: 'Total Leads',
                data: this.state.get_quote_graph_company.total_leads,
                backgroundColor: ["#3e6a8f","#f09f5f","#8d629d","#d2aca3","#cacdcf","#eec8a5","#75aede","#72c4af"],
              }
            ]
          };


        if (this.chartRefQuoteCompany && this.chartRefQuoteCompany.el) {
            this.chartQuoteCompany = new Chart(this.chartRefQuoteCompany.el, {
                type: 'pie',
                data: data,
                options: {
                    responsive: true,
                    plugins: {
                    legend: {
                        display:false
                    },
                    title: {
                        display: false,
                       
                    }
                    }
                },
            });
            let id='legend1'
            this.createCustomLegend(data,id);
        }

    }





    getquoteproductwisegraph = ()=>{
        if (this.chartQuoteProduct) {
            this.chartQuoteProduct.destroy();  // Destroy the old chart instance
        }


        const generateColors = (length) => {
        const colors = [];
        const step = 360 / length; // Spread colors evenly across the hue spectrum
        for (let i = 0; i < length; i++) {
            let hue = Math.floor(i * step); // Ensure distinct colors
            colors.push(`hsl(${hue}, 62%, 72%)`); // Light colors with 60% saturation, 75% lightness
        }
        return colors;
    };

    const productData = this.state.get_quote_graph_product;
    console.log("this is my getquoteproductwisegraph valueod product data",productData)
    const dataLength = productData.product.length;
    const line_data = productData.revenue.map(value => value + 10000);

    const backgroundColors = generateColors(dataLength);
       

        
        const data = {
            labels: productData.product ,
            datasets: [
                {
                    label:'Revenue',
                    data:productData.revenue,
                    type: 'bar',
                    backgroundColor:backgroundColors,
                    yAxisID: 'y',  // Uses primary y-axis
                    order: 1, // Ensures it appears behind the line chart
                    borderWidth:1,
                    barPecentage:0.5      
                  }
                  ,{
                    label: 'Total Leads',
                    data: productData.total_leads,
                    backgroundColor: backgroundColors,
                    // data:line_data,
                     type: 'line',
                    borderColor: 'black', 
                    backgroundColor: backgroundColors, // Dynamic colors
                    borderWidth: 2,  // Line thickness
                    tension: 0.4, // Smooth the line
                    yAxisID: 'y1',  // Uses secondary y-axis
                    order: 0  // Ensures it appears above the bar chart
                  }
            ]
          };


        if (this.chartRefQuoteProduct && this.chartRefQuoteProduct.el) {
            this.chartQuoteProduct = new Chart(this.chartRefQuoteProduct.el, {
                type: 'scatter',
                data: data,
                options: {
                    responsive: true,
                     scales: {
                       
                  y: {
                        type: 'linear',
                        position: 'left',
                       display:false,
                        ticks: {
                            display: false,
                          },
                        beginAtZero: true,
                        grid: { drawOnChartArea: false } // Removes grid lines from overlapping
                        
                    },
                    y1: {
                        type: 'linear',
                        position: 'right',
                         display:false,
                        
                        beginAtZero: true,
                        grid: { drawOnChartArea: false }, // Keeps both charts separate
                        ticks: {
                            color: 'red'  // Makes y1 axis labels red for clarity
                        }
                    }
                     },
                    plugins: {
                        tooltip: {
                            callbacks: {
                                label: function(tooltipItem) {
                                    if (tooltipItem.datasetIndex === 1) { // Line chart dataset
                                        return `Total Leads: ${productData.total_leads[tooltipItem.dataIndex]}`; // Show modified value
                                    } 
                                }
                            }
                        },
                        legend: {
                            display:false,
                        },
                        title: {
                            display: false,
                           
                        }
                        }
                },
            });
            // let id='legend2'
            // this.createCustomLegend(data,id);
        }

    }


getwoncompanywisegraph = ()=>{
        if (this.chartWonStage) {
            this.chartWonStage.destroy();  // Destroy the old chart instance
        }

    console.log("this is my won stage graph rendering")
       
    // Function to generate distinct light colors
    const generateColors = (length) => {
        const colors = [];
        const step = 360 / length; // Spread colors evenly across the hue spectrum
        for (let i = 0; i < length; i++) {
            let hue = Math.floor(i * step); // Ensure distinct colors
            colors.push(`hsl(${hue}, 60%, 75%)`); // Light colors with 60% saturation, 75% lightness
        }
        return colors;
    };

    const companyData = this.state.get_won_graph_company;
    const dataLength = companyData.tag_name.length;
    const line_data = companyData.revenue.map(value => value + 10000);
    const backgroundColors = generateColors(dataLength);

    console.log("this is my won stage graph rendering 22",companyData,dataLength,line_data,backgroundColors)

    const data = {
        labels: companyData.tag_name,
        datasets: [

           
            {
                label: 'Revenue',
                type: 'bar',
                data: companyData.revenue,
                backgroundColor: backgroundColors, // Dynamic colors
                yAxisID: 'y',  // Uses primary y-axis
                order: 1, // Ensures it appears behind the line chart
                borderWidth:1,
                barPecentage:0.5              
            },

             {
                label: 'Total Leads',
                type: 'line',
                data: companyData.total_leads,
                 // data:line_data,
               borderColor: 'black',  // Line color
                backgroundColor: backgroundColors, // Dynamic colors
                borderWidth: 2,  // Line thickness
                tension: 0.4, // Smooth the line
                yAxisID: 'y1',  // Uses secondary y-axis
                order: 0  // Ensures it appears above the bar chart
            },
            
        ]
    };

       


        if (this.chartRefWonStage && this.chartRefWonStage.el) {
            this.chartWonStage = new Chart(this.chartRefWonStage.el, {
                type: 'scatter',
                data: data,
                options: {
                    responsive: true,
                     scales: {
                       
                  y: {
                        type: 'linear',
                        position: 'left',
                       display:false,
                        beginAtZero: true,
                       ticks: {
                            display: false,
                          },
                        grid: { drawOnChartArea: false } // Removes grid lines from overlapping
                        
                    },
                    y1: {
                        type: 'linear',
                        position: 'right',
                         display:false,
                        beginAtZero: true,
                        grid: { drawOnChartArea: false }, // Keeps both charts separate
                        ticks: {
                            color: 'red'  // Makes y1 axis labels red for clarity
                        }
                    }
                     },
                    plugins: {
                           tooltip: {
                            callbacks: {
                                label: function(tooltipItem) {
                                    if (tooltipItem.datasetIndex === 1) { // Line chart dataset
                                        return `Total Leads: ${companyData.total_leads[tooltipItem.dataIndex]}`; // Show modified value
                                    } 
                                }
                            }
                        },
                    legend: {
                        display:false
                    },
                    title: {
                        display: false,
                       
                    }
                    }
                },
            });
            // let id='legend1'
            // this.createCustomLegend(data,id);
        }

    }


    





    getquotecompanywisegraph = ()=>{
        if (this.chartQuoteCompany) {
            this.chartQuoteCompany.destroy();  // Destroy the old chart instance
        }
       
    // Function to generate distinct light colors
    const generateColors = (length) => {
        const colors = [];
        const step = 360 / length; // Spread colors evenly across the hue spectrum
        for (let i = 0; i < length; i++) {
            let hue = Math.floor(i * step); // Ensure distinct colors
            colors.push(`hsl(${hue}, 60%, 75%)`); // Light colors with 60% saturation, 75% lightness
        }
        return colors;
    };

    const companyData = this.state.get_quote_graph_company;
    const dataLength = companyData.tag_name.length;
    const line_data = companyData.revenue.map(value => value + 10000);
    const backgroundColors = generateColors(dataLength);

    const data = {
        labels: companyData.tag_name,
        datasets: [

           
            {
                label: 'Revenue',
                type: 'bar',
                data: companyData.revenue,
                backgroundColor: backgroundColors, // Dynamic colors
                yAxisID: 'y',  // Uses primary y-axis
                order: 1, // Ensures it appears behind the line chart
                borderWidth:1,
                barPecentage:0.5              
            },

             {
                label: 'Total Leads',
                type: 'line',
                data: companyData.total_leads,
                 // data:line_data,
               borderColor: 'black',  // Line color
                backgroundColor: backgroundColors, // Dynamic colors
                borderWidth: 2,  // Line thickness
                tension: 0.4, // Smooth the line
                yAxisID: 'y1',  // Uses secondary y-axis
                order: 0  // Ensures it appears above the bar chart
            },
            
        ]
    };

       


        if (this.chartRefQuoteCompany && this.chartRefQuoteCompany.el) {
            this.chartQuoteCompany = new Chart(this.chartRefQuoteCompany.el, {
                type: 'scatter',
                data: data,
                options: {
                    responsive: true,
                     scales: {
                       
                  y: {
                        type: 'linear',
                        position: 'left',
                       display:false,
                        beginAtZero: true,
                       ticks: {
                            display: false,
                          },
                        grid: { drawOnChartArea: false } // Removes grid lines from overlapping
                        
                    },
                    y1: {
                        type: 'linear',
                        position: 'right',
                         display:false,
                        beginAtZero: true,
                        grid: { drawOnChartArea: false }, // Keeps both charts separate
                        ticks: {
                            color: 'red'  // Makes y1 axis labels red for clarity
                        }
                    }
                     },
                    plugins: {
                           tooltip: {
                            callbacks: {
                                label: function(tooltipItem) {
                                    if (tooltipItem.datasetIndex === 1) { // Line chart dataset
                                        return `Total Leads: ${companyData.total_leads[tooltipItem.dataIndex]}`; // Show modified value
                                    } 
                                }
                            }
                        },
                    legend: {
                        display:false
                    },
                    title: {
                        display: false,
                       
                    }
                    }
                },
            });
            // let id='legend1'
            // this.createCustomLegend(data,id);
        }

    }




    getforecastproductwisegraph_pie = ()=>{
        if (this.chartforecastProduct) {
            this.chartforecastProduct.destroy();  // Destroy the old chart instance
        }


        const generateColors = (length) => {
        const colors = [];
        const step = 360 / length; // Spread colors evenly across the hue spectrum
        for (let i = 0; i < length; i++) {
            let hue = Math.floor(i * step); // Ensure distinct colors
            colors.push(`hsl(${hue}, 62%, 72%)`); // Light colors with 60% saturation, 75% lightness
        }
        return colors;
    };

    const productData = this.state.get_forecast_graph_product;
        console.log("this is my getforecastproductwisegraph valueod product data",productData)
    const dataLength = productData.product.length;

    const backgroundColors = generateColors(dataLength);

       
        
        const data = {
            labels: productData.product,
            datasets: [
                {
                    label:'Revenue',
                    data:productData.revenue,
                    backgroundColor:backgroundColors,
                  }
                  // ,{
                  //   label: 'Total Leads',
                  //   data: this.state.get_forecast_graph_product.total_leads,
                  //   backgroundColor: ["#3e6a8f","#f09f5f","#8d629d","#d2aca3","#cacdcf","#eec8a5","#75aede","#72c4af"],
                  // }
            ]
          };


        if (this.chartRefforecastProduct && this.chartRefforecastProduct.el) {
            this.chartforecastProduct = new Chart(this.chartRefforecastProduct.el, {
                type: 'pie',
                data: data,
                options: {
                    responsive: true,
                    plugins: {
                       
                        legend: {
                            display:false
                        },
                        title: {
                            display: false,
                           
                        }
                        }
                },
            });
            let id='legend4'
            this.createCustomLegend(data,id);
        }

    }





    getforecastcompanywisegraph_pie = ()=>{
        if (this.chartforecastCompany) {
            this.chartforecastCompany.destroy();  // Destroy the old chart instance
        }


        const generateColors = (length) => {
        const colors = [];
        const step = 360 / length; // Spread colors evenly across the hue spectrum
        for (let i = 0; i < length; i++) {
            let hue = Math.floor(i * step); // Ensure distinct colors
            colors.push(`hsl(${hue}, 62%, 72%)`); // Light colors with 60% saturation, 75% lightness
        }
        return colors;
    };

    const companyData = this.state.get_forecast_graph_company;
    const dataLength = companyData.tag_name.length;

    const backgroundColors = generateColors(dataLength);

       
        
        const data = {
            labels: companyData.tag_name,
            datasets: [
              {
                label: 'Revenue',
                data: companyData.revenue,
                backgroundColor:backgroundColors,
              }
            //   ,{
            //     label: 'Total Leads',
            //     data: this.state.get_forecast_graph_company.total_leads,
            //     backgroundColor: ["#3e6a8f","#f09f5f","#8d629d","#d2aca3","#cacdcf","#eec8a5","#75aede","#72c4af"],
            //   }
            ]
          };


        if (this.chartRefforecastCompany && this.chartRefforecastCompany.el) {
            this.chartforecastCompany = new Chart(this.chartRefforecastCompany.el, {
                type: 'pie',
                data: data,
                options: {
                    responsive: true,
                    plugins: {
                    legend: {
                        display:false
                    },
                    title: {
                        display: false,
                       
                    }
                    }
                },
            });
            let id='legend3'
            this.createCustomLegend(data,id);
        }

    }



       getforecastproductwisegraph = ()=>{
        if (this.chartforecastProduct) {
            this.chartforecastProduct.destroy();  // Destroy the old chart instance
        }


        const generateColors = (length) => {
        const colors = [];
        const step = 360 / length; // Spread colors evenly across the hue spectrum
        for (let i = 0; i < length; i++) {
            let hue = Math.floor(i * step); // Ensure distinct colors
            colors.push(`hsl(${hue}, 62%, 72%)`); // Light colors with 60% saturation, 75% lightness
        }
        return colors;
    };

    // const productData = this.state.get_forecast_graph_product;
    //     console.log("this is my getforecastproductwisegraph valueod product data",productData)
    // const dataLength = productData.product.length;

    // const backgroundColors = generateColors(dataLength);


        const productData = this.state.get_forecast_graph_product;
      
        const dataLength = productData.product.length;
        const line_data = productData.revenue.map(value => value + 100000);
        
        const backgroundColors = generateColors(dataLength);
           

       
        
        const data = {
            labels: productData.product,
            datasets: [
                {
                    label:'Revenue',
                    data:productData.revenue,
                    backgroundColor:backgroundColors,
                     type: 'bar',
                    backgroundColor:backgroundColors,
                    yAxisID: 'y',  // Uses primary y-axis
                    order: 1, // Ensures it appears behind the line chart
                    borderWidth:1,
                    barPecentage:0.5  
                  },
                 {
                label: 'Total Leads',
                data: productData.total_leads,
                backgroundColor: backgroundColors,
                // data:line_data,
                 type: 'line',
                borderColor: 'black', 
                backgroundColor: backgroundColors, // Dynamic colors
                borderWidth: 2,  // Line thickness
                tension: 0.4, // Smooth the line
                yAxisID: 'y1',  // Uses secondary y-axis
                order: 0  // Ensures it appears above the bar chart
              }
                
            ]
          };


        if (this.chartRefforecastProduct && this.chartRefforecastProduct.el) {
            this.chartforecastProduct = new Chart(this.chartRefforecastProduct.el, {
                type: 'scatter',
                data: data,
                options: {
                     scales: {
                   
              y: {
                    type: 'linear',
                    position: 'left',
                   display:false,
                    ticks: {
                        display: false,
                      },
                    beginAtZero: true,
                    grid: { drawOnChartArea: false } // Removes grid lines from overlapping
                    
                },
                y1: {
                    type: 'linear',
                    position: 'right',
                     display:false,
                    
                    beginAtZero: true,
                    grid: { drawOnChartArea: false }, // Keeps both charts separate
                    ticks: {
                        color: 'red'  // Makes y1 axis labels red for clarity
                    }
                }
                 },
                    responsive: true,
                    plugins: {
                         tooltip: {
                        callbacks: {
                            label: function(tooltipItem) {
                                if (tooltipItem.datasetIndex === 1) { // Line chart dataset
                                    return `Total Leads: ${productData.total_leads[tooltipItem.dataIndex]}`; // Show modified value
                                } 
                            }
                        }
                    },
                       
                        legend: {
                            display:false
                        },
                        title: {
                            display: false,
                           
                        }
                        }
                },
            });
            // let id='legend4'
            // this.createCustomLegend(data,id);
        }

    }





    getforecastcompanywisegraph = ()=>{
        if (this.chartforecastCompany) {
            this.chartforecastCompany.destroy();  // Destroy the old chart instance
        }


        const generateColors = (length) => {
        const colors = [];
        const step = 360 / length; // Spread colors evenly across the hue spectrum
        for (let i = 0; i < length; i++) {
            let hue = Math.floor(i * step); // Ensure distinct colors
            colors.push(`hsl(${hue}, 62%, 72%)`); // Light colors with 60% saturation, 75% lightness
        }
        return colors;
    };

    // const companyData = this.state.get_forecast_graph_company;
    // const dataLength = companyData.tag_name.length;

    // const backgroundColors = generateColors(dataLength);

    const companyData = this.state.get_forecast_graph_company;
    const dataLength = companyData.tag_name.length;
    const line_data = companyData.revenue.map(value => value + 10000);
    const backgroundColors = generateColors(dataLength);
           
        
        const data = {
            labels: companyData.tag_name,
            datasets: [
              {
                label: 'Revenue',
                type: 'bar',
                data: companyData.revenue,
                backgroundColor:backgroundColors,
                yAxisID: 'y',  // Uses primary y-axis
                order: 1, // Ensures it appears behind the line chart
                borderWidth:1,
                barPecentage:0.5     
              },
              {
                label: 'Total Leads',
                type: 'line',
                data: companyData.total_leads,
                // data:line_data,
                borderColor: 'black',  // Line color
                backgroundColor: backgroundColors, // Dynamic colors
                borderWidth: 2,  // Line thickness
                tension: 0.4, // Smooth the line
                yAxisID: 'y1',  // Uses secondary y-axis
                order: 0  // Ensures it appears above the bar chart
            },
           
            ]
          };


        if (this.chartRefforecastCompany && this.chartRefforecastCompany.el) {
            this.chartforecastCompany = new Chart(this.chartRefforecastCompany.el, {
                type: 'scatter',
                data: data,
                options: {
                    scales: {
                   
              y: {
                    type: 'linear',
                    position: 'left',
                   display:false,
                    beginAtZero: true,
                   ticks: {
                        display: false,
                      },
                    grid: { drawOnChartArea: false } // Removes grid lines from overlapping
                    
                },
                y1: {
                    type: 'linear',
                    position: 'right',
                     display:false,
                    beginAtZero: true,
                    grid: { drawOnChartArea: false }, // Keeps both charts separate
                    ticks: {
                        color: 'red'  // Makes y1 axis labels red for clarity
                    }
                }
                 },
                    responsive: true,
                    plugins: {
                         tooltip: {
                        callbacks: {
                            label: function(tooltipItem) {
                                if (tooltipItem.datasetIndex === 1) { // Line chart dataset
                                    return `Total Leads: ${companyData.total_leads[tooltipItem.dataIndex]}`; // Show modified value
                                } 
                            }
                        }
                    },
                    legend: {
                        display:false
                    },
                    title: {
                        display: false,
                       
                    }
                    }
                },
            });
            // let id='legend3'
            // this.createCustomLegend(data,id);
        }

    }




    createCustomLegend = (data,id) => {
        let dataset = data.datasets[1] ? data.datasets[1] : data.datasets[0]; // Use only the first dataset
        let legendHTML = '<ul class="custom-legend">';
    
        data.labels.forEach((label, index) => {
            legendHTML += `
                <li>
                <div class="legendValue"><span style="background-color:${dataset.backgroundColor[index]};"></span><p>${label}</p></div> 
                </li>
                
            `;
        });
    
        legendHTML += '</ul>';
    
        // Insert the legend into the div
        document.getElementById(id).innerHTML = legendHTML;
    };



    async redirectToListView(model_name, title, domain = [],context={},current_view=null) {
        if (!model_name) return;
           // Save current filters before navigating away
        sessionStorage.setItem("crm_filters", JSON.stringify({
            team_id:this.state.team_id,
            comp_id:this.state.comp_id,
            user_id:this.state.user_id,
            product_id:this.state.product_id,
            job_id:this.state.job_id,
            select_month:this.state.select_month,
            filterLists:this.state.filterLists,
          
        }));
        sessionStorage.setItem('current_view', current_view);  

        await this.env.services.action.doAction({
            type: 'ir.actions.act_window',
            res_model: model_name,
            view_mode: 'list,form',  // Enables both list & form view
            views: [[false, "list"], [false, "form"]],
            domain: domain,
            name: title,
            target: "current", // Ensures it opens in the current window
           context:{
            ...context
           }
        });
    }

     formatDate(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0'); // Months are 0-indexed
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    
    async Onclick_getorderbooking_achieve() {
       

            let domain=this.state.getorderbooking.domain_main
            let current_view = 'main-page'
            console.log("this is my domain of achived by a state",domain)
            let context = {
                'group_by': ['tag_ids'] // Group by user_id
                };
        await this.redirectToListView('crm.lead', 'Order Booking Achievements', domain,context,current_view);
    }

    
    async Onclick_getorderbooking_others (){
          try {
            
            let today = new Date();
            let currentYear = today.getFullYear();  // Get the current year
            let current_view = 'main-page'
            let domain=this.state.getorderbooking.domain_others

           
                
            if (!domain || domain.length === 0) {
                    domain = [["id", "=", -1]];  // This will return no records
                }

            console.log("this is my domain of others by astate",domain)
            let context = {
                'group_by': ['tag_ids'] // Group by user_id
                };
        await this.redirectToListView('crm.lead', 'Order Booking Others', domain,context,current_view);
    
        } catch (error) {
            console.error("Error in Onclick_getorderbooking_target:", error);
           
    }
        
    }
    async Onclick_getorderbooking_target() {
        try {
            
            let today = new Date();
            let currentYear = today.getFullYear();  // Get the current year
            let current_view = 'main-page'
            let domain=this.state.getorderbooking.target_domain

            console.log("this is my domain of achived by astate",domain)
    

              let context = {
                'group_by': ["x_studio_division_1"] // Group by user_id
                };
           
            await this.redirectToListView('hr.employee.target', 'Order Booking Targets', domain,context,current_view);
    
        } catch (error) {
            console.error("Error in Onclick_getorderbooking_target:", error);
        }
    }
    



     async Onclick_getorder_invoice_achieve() {
       

        let domain= this.state.getorderrevenue.target_domain
        let current_view = 'main-page'
        let context = {
                'group_by': ["tag_id"] // Group by user_id
                };
        // Redirect to sale.order list view with domain filter
        await this.redirectToListView('monthly.crm.revenue.line', 'Order Invoice Achievements', domain,context,current_view);
    }


   

    async Onclick_get_quote_submitted() {
          
                try {
                    let domain = this.state.get_quote_submitted.domain
                    let current_view = 'main-page'
           
                    console.log("Final domain for quote submitted data:", domain);
            
                    // Redirect to CRM Lead List View
                     let context = {
                            'group_by': ['user_id'] // Group by user_id
                        };
                    await this.redirectToListView("crm.lead", "Quote Submitted Leads", domain,context,current_view);
                } catch (error) {
                    console.error("Error in getQuotesFunction:", error);
                }
            }

    

async onclick_employee_payment_collection(type) {
    try {
        let domain = [];
        let current_view = 'fourth-page'
        if (this.state.get_employee_payment_totals.domain){
            domain = this.state.get_employee_payment_totals.domain
        }
           if (type && type !== 'total') {
        domain.push(['due_type', '=', type]);
        }

       
        let context = {};

        console.log("Final domain for employee collection:", domain,type);

        await this.redirectToListView("employee.payment.collection.line", "Employees Paymnet Collection", domain, context,current_view);

    } catch (error) {
        console.error("Error in onclick_employee_payment_collection:", error);
    }
}
    
    async Onclick_get_probability_values(type) {
       
            try {
                
               //  let domain = [];
               //  console.log("ths is the type of pipeline",type)
              let domain = this.state.get_probability_values[1]?.domain || [];
              let current_view = 'second-page'
              console.log("ths is  of pipeline ======================== first [1]",this.state.get_probability_values[1].domain)
        
            
              
               //  // Define probability stages
                let stages = []
                if (type){
                    if (type == 'Expecting 60%'){
                        type = 'Expecting (60%)'
                    }
                     if (type == 'Commit 90%'){
                        type = 'Commit (90%)'
                    }
                    stages.push(type)
                    console.log("this is my stage of the probability",stages)
                }
        
                let stage_records = await this.orm.searchRead("crm.stage", [['name', 'in', stages]], ['id']);
                let stage_list = stage_records.map(stage => stage.id);
        
                if (stage_list.length === 0) {
                    console.error("Probability stages not found.");
                    return;
                }
        
                
                domain.push(['stage_id', 'in', stage_list]);
             
        
              
               console.log("ths is  of pipeline ======================== domain", domain)
             
        
                console.log("Final domain for probability leads:", domain);
                 let context = {
                        // 'group_by': ['stage_id'] // Group by stage_id
                    };
                // Redirect to CRM Lead List View
                await this.redirectToListView("crm.lead", "Probability Leads", domain,context,current_view);
            } catch (error) {
                console.error("Error in getProbabilityFunction:", error);
            }
        }
        
    
     async Onclick_getPlannedActivityToday() {
    try {
       
       
        let domain = []
          let context = {};
        let current_view = 'third-page'
        if (this.state.get_activity_value.domain.planning_today){
                    domain.push(['id','in',this.state.get_activity_value.domain.planning_today])
                }

        console.log("Planned Activities (Today) Domain:", domain);
        await this.redirectToListView("mail.activity", "Planned Activities Today", domain,context,current_view);
       
    } catch (error) {
        console.error("Error in Onclick_getPlannedActivityToday:", error);
    }
}

        


        async Onclick_getPlannedActivityMonth() {
            try {
                let domain = []
                  let context = {};
                let current_view = 'third-page'
                if (this.state.get_activity_value.domain.planning_month){
                    domain.push(['id','in',this.state.get_activity_value.domain.planning_month])
                }
               
                console.log("Planned Activities (Month) Domain:", domain);
                await this.redirectToListView("mail.activity", "Planned Activities Month", domain,context,current_view);
               
            } catch (error) {
                console.error("Error in Onclick_getPlannedActivityMonth:", error);
            }
        }
        

        async Onclick_getDoneActivityToday() {
            try {
             
                let domain = []
                 let current_view = 'third-page'
                  let context = {};
                if (this.state.get_activity_value.domain.done_today){
                    domain.push(['id','in',this.state.get_activity_value.domain.done_today])
                }
               
        
             
                console.log("Completed Activities (Today) Domain:", domain);
        
                await this.redirectToListView("crm.done.activitys", "Done Activities Today", domain,context,current_view);
               
            } catch (error) {
                console.error("Error in Onclick_getDoneActivityToday:", error);
            }
        }
        



        async Onclick_getDoneActivityMonth() {
            try {
      
                let domain = []
                 let context = {};
                let current_view = 'third-page'
                if (this.state.get_activity_value.domain.done_month){
                    domain.push(['id','in',this.state.get_activity_value.domain.done_month])
                }
        
                console.log("Completed Activities (Month) Domain:", domain);
                
                await this.redirectToListView("crm.done.activitys", "Done Activities Month", domain,context,current_view);
               
                
            } catch (error) {
                console.error("Error in Onclick_getDoneActivityMonth:", error);
            }      
        }




async Onclick_get_won_stage_company_graph() {
   try {
        if (this.state.get_won_graph_company.domain){
                
            let domain=this.state.get_won_graph_company.domain
             let current_view = 'second-page'
  
        console.log("Final domain for Onclick_get_won_stage_company_graph:", domain);

        // Redirect to CRM Lead List View
         let groupByField = this.state.comp_id ? 'user_id' : 'tag_ids';
         let context = {
                group_by: [groupByField]
            };
        await this.redirectToListView("crm.lead", "Won Stage Company wise", domain, context,current_view);
        }

    } catch (error) {
        console.error("Error in Onclick_get_won_stage_company_graph:", error);
    }
}




       
    async Onclick_get_quote_submitted_company_graph() {
          
        try {
            
         if (this.state.get_quote_graph_company.domain){
                
            let domain=this.state.get_quote_graph_company.domain
            let current_view = 'third-page'
        
            console.log("Final domain for quote submitted data:", domain);
    
            // Redirect to CRM Lead List View
            let groupByField = this.state.comp_id ? 'user_id' : 'tag_ids';
            let context = {
                group_by: [groupByField]
            };
            await this.redirectToListView("crm.lead", "Quote Submitted Company wise", domain,context,current_view);
         }
        } catch (error) {
            console.error("Error in Onclick_get_quote_submitted_company_graph:", error);
        }
    }
        


    async Onclick_get_quote_submitted_product_graph() {
          
        try {
            if (this.state.get_quote_graph_product.domain){
                
            let domain=this.state.get_quote_graph_product.domain
             let current_view = 'fourth-page'
       
    
            console.log("Final domain for quote submitted data:", domain);
    
            // Redirect to CRM Lead List View
             let context = {
                    'group_by': ['x_studio_product_category_1'] // Group by user_id
                };
            await this.redirectToListView("crm.lead", "Quote Submitted Product Wise", domain,context,current_view);
            }
        } catch (error) {
            console.error("Error in Onclick_get_quote_submitted_product_graph:", error);
        }
    }
        
    async Onclick_get_forecast_company_graph() {
          
        try {
            if (this.state.get_forecast_graph_company.domain){
            let domain=this.state.get_forecast_graph_company.domain
              let current_view = 'forecast-page'
       
    
            console.log("Final domain for quote submitted data:", domain);
    
            // Redirect to CRM Lead List View
          
            let groupByField = this.state.comp_id ? 'user_id' : 'tag_ids';
            let context = {
                group_by: [groupByField]
            };
            await this.redirectToListView("crm.lead", "Forecast Records: Company wise", domain,context,current_view);
            }
        } catch (error) {
            console.error("Error in Onclick_get_forecast_company_graph:", error);
        }
    }
        



    async Onclick_get_forecast_product_graph() {
          
        try {
            let domain =this.state.get_forecast_graph_product.domain
             let current_view = 'forecast-page'
           
    
            console.log("Final domain for quote submitted data:", domain);
    
            // Redirect to CRM Lead List View
             let context = {
                    'group_by': [this.state.comp_id ? 'user_id': 'x_studio_product_category_1'] // Group by user_id
                };
            await this.redirectToListView("crm.lead", "Forecast Records :Product wise ", domain,context,current_view);
        } catch (error) {
            console.error("Error in Onclick_get_forecast_product_graph:", error);
        }
    }




    async Onclick_get_activity_view(id) {
    try {
        let domain = [];
        let context = {};
        let res_model = null;
        let current_view = 'mail-activity-page'

        // Log for debug
        console.log("Activity List:", this.state.get_mail_activity_lists.formatted_activities);
        
        // Check if activity list exists and is an array
        const activityList = this.state.get_mail_activity_lists.formatted_activities;
        if (Array.isArray(activityList) && id) {
            // Find the activity by id
            const activity = activityList.find(item => item.res_id === id);
            if (activity) {
                res_model = activity.res_model;
                domain.push(['id', '=', id]);
            } else {
                console.warn(`Activity with id ${id} not found.`);
            }
        } else {
            console.warn("Activity list not available or ID is missing.");
        }

        console.log("This is my model in activity list:", res_model);

        if (res_model) {
            await this.redirectToListView(res_model, "Activity Document Details", domain, context,current_view);
        } else {
            console.warn("res_model is undefined, not redirecting.");
        }

    } catch (error) {
        console.error("Error in Onclick_get_activity_view:", error);
    }
}






    async Onclick_new_get_employee_payment_totals(status = null,id) {
                let records = this.state.new_get_employee_payment_totals.summary;
            
                // Base domain: Filter by record_ids
                let domain = [['divition_id', '=', id]];
            
                // Add due_status to domain if provided
                if (status) {
                    domain.push(['due_status', '=', status]);
                }
            
                console.log("Redirect domain:", domain);
            
                let context = {};
                let current_view = 'payment-page'

            
                // Redirect to list view with filtered domain
                await this.redirectToListView(
                    'report.employee.payment.grouped',
                    'Payment Collection Report',
                    domain,
                    context,
                    current_view
                );
            }


        async Onclick_get_realization_summary(record_id) {
            // Clone the domain to avoid mutating shared state
            let domain = [...this.state.get_realization_summary_domain];
        
            domain.push(['total_verified_amount', '>', 0.00]);
        
            if (this.state.comp_id) {
                domain.push(['employee_id', '=', record_id]);
            } else {
                domain.push(['divition_id', '=', record_id]);
            }
        
            console.log("this is my domain in Onclick_get_realization_summary", domain);
            
            let context = {};
            let current_view = 'realization-page';
        
            await this.redirectToListView(
                'report.employee.payment.grouped',
                'Realization Summary',
                domain,
                context,
                current_view
            );
        }



    realizationTotalRow() {
        const rows = this.state.get_realization_summary.result || [];
        console.log("this is iiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiiii row",rows)
        const total = {
            order: "Total",
            outstanding: 0,
            current_month_pdc: 0,
            future_month_pdc: 0,
            collection_current: 0,
            collection_pdc: 0,
            balance_realise_current: 0,
            balance_realise_future: 0,
            total_collection: 0,
            total_realised: 0,
        };
    
        const parse = (val) => parseFloat((val || "0").replace(/,/g, ""));
    
        for (const row of rows) {
            total.outstanding += parse(row.outstanding);
            total.current_month_pdc += parse(row.current_month_pdc);
            total.future_month_pdc += parse(row.future_month_pdc);
            total.collection_current += parse(row.collection_current);
            total.collection_pdc += parse(row.collection_pdc);
            total.balance_realise_current += parse(row.balance_realise_current);
            total.balance_realise_future += parse(row.balance_realise_future);
            total.total_collection += parse(row.total_collection);
            total.total_realised += parse(row.total_realised);
            
        }
    
        const format = (num) => num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    
        let result= {
            order: "Total",
            outstanding: format(total.outstanding),
            current_month_pdc: format(total.current_month_pdc),
            future_month_pdc: format(total.future_month_pdc),
            collection_current: format(total.collection_current),
            collection_pdc: format(total.collection_pdc),
            balance_realise_current: format(total.balance_realise_current),
            balance_realise_future: format(total.balance_realise_future),
            total_collection: format(total.total_collection),
            total_realised: format(total.total_realised),
        };
        console.log("thhis is my total realization data ",result)
        
        this.state.total_realization_summary = result
       
    }


 



     formatTotalSummaryRow() {
        let userSummaries = this.state.new_get_employee_payment_totals.summary
                const total = {
                    total_outstanding: 0,
                    total_collected: 0,
                    overdue_outstanding: 0,
                    overdue_collected: 0,
                    due_outstanding: 0,
                    due_collected: 0,
                    nodue_outstanding: 0,
                    nodue_collected: 0,
                };
            
                const parse = (val) => parseFloat((val || "0").toString().replace(/,/g, ''));
            
                userSummaries.forEach(user => {
                    user.summary.forEach(item => {
                        const status = item.status;
                        const amount = parse(item.amount);
                        const collected = parse(item.collected);
            
                        if (status === "total") {
                            total.total_outstanding += amount;
                            total.total_collected += collected;
                        } else if (status === "overdue") {
                            total.overdue_outstanding += amount;
                            total.overdue_collected += collected;
                        } else if (status === "due") {
                            total.due_outstanding += amount;
                            total.due_collected += collected;
                        } else if (status === "nodue") {
                            total.nodue_outstanding += amount;
                            total.nodue_collected += collected;
                        }
                    });
                });
            
                const getPercent = (collected, amount) =>
                    amount ? ((collected / amount) * 100).toFixed(1) + "%" : "0.0%";
            
                let result= {
                    key: "Total",
                    total_outstanding: total.total_outstanding.toLocaleString(undefined, { minimumFractionDigits: 2 }),
                    total_collected: total.total_collected.toLocaleString(undefined, { minimumFractionDigits: 2 }),
                    total_percentage: getPercent(total.total_collected, total.total_outstanding),
            
                    overdue_outstanding: total.overdue_outstanding.toLocaleString(undefined, { minimumFractionDigits: 2 }),
                    overdue_collected: total.overdue_collected.toLocaleString(undefined, { minimumFractionDigits: 2 }),
                    overdue_percentage: getPercent(total.overdue_collected, total.overdue_outstanding),
            
                    due_outstanding: total.due_outstanding.toLocaleString(undefined, { minimumFractionDigits: 2 }),
                    due_collected: total.due_collected.toLocaleString(undefined, { minimumFractionDigits: 2 }),
                    due_percentage: getPercent(total.due_collected, total.due_outstanding),
            
                    nodue_outstanding: total.nodue_outstanding.toLocaleString(undefined, { minimumFractionDigits: 2 }),
                    nodue_collected: total.nodue_collected.toLocaleString(undefined, { minimumFractionDigits: 2 }),
                    nodue_percentage: getPercent(total.nodue_collected, total.nodue_outstanding),
                };

             this.state.total_payment_summary=result
            }





    
}   
registry.category("actions").add("custom_crm_dashboard", CrmDashboard);
CrmDashboard.template = "CrmDashboard";
