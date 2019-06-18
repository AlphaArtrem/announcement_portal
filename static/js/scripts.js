/*
Posting form an anchor tag insted of getting
*/
function DoPost(pageno)
{
    $.post("/announcement", { page : pagno  } );
}
